<script setup>
import { computed, onBeforeUnmount, onMounted, ref, watch } from "vue";
import { useRouter } from "vue-router";
import WordCard from "../components/WordCard.vue";
import * as api from "../api";
import { familyById, human, startSession, state } from "../store";

const props = defineProps({ id: { type: String, required: true } });
const router = useRouter();
const fallback = ref(null);
const missing = ref(false);
const zoomed = ref(null);

const family = computed(() => familyById(props.id) || fallback.value);
const freshCount = computed(() => family.value ? family.value.total - family.value.learned : 0);
const missingImgs = computed(() =>
  family.value ? family.value.words.filter((w) => !w.img).length : 0);
// 智能体画的图落在 /media，手绘的种子插画在 /assets，只有前者能覆盖重画。
const generated = computed(() => !!zoomed.value && zoomed.value.img.includes("/media/"));

const drawing = ref("");     // 正在单独配图的词
const filling = ref(null);   // 整族补图的进度 { done, total }
const imgError = ref("");
let fillTimer = null;

async function resolve() {
  missing.value = false;
  if (family.value) return;
  try {
    fallback.value = await api.fetchFamily(props.id);
  } catch {
    missing.value = true;
  }
}
onMounted(resolve);
watch(() => props.id, resolve);

async function start(pool) {
  if (await startSession({ mode: "practice", familyId: family.value.id, pool })) {
    router.push({ name: "quiz" });
  }
}

// 画好一张就贴一张：直接改 store 里那个词对象，不用整库重拉。
function applyImage(item) {
  const target = family.value && family.value.words.find((w) => w.word === item.word);
  if (target && item.ok !== false && item.img) {
    target.img = item.img;
    target.imgZh = item.imgZh;
  }
}

async function drawOne(word) {
  drawing.value = word;
  imgError.value = "";
  try {
    applyImage(await api.drawWord(word));
  } catch (e) {
    imgError.value = e.message;
  } finally {
    drawing.value = "";
  }
}

function stopFill() {
  if (fillTimer) clearInterval(fillTimer);
  fillTimer = null;
}
onBeforeUnmount(stopFill);

// 整族补图走后台任务，一张一张画，轮询进度。
async function fillFamily() {
  if (filling.value || !family.value) return;
  imgError.value = "";
  let job;
  try {
    job = await api.startFamilyImages(family.value.id);
  } catch (e) {
    imgError.value = e.message;
    return;
  }
  filling.value = { done: 0, total: job.total };
  fillTimer = setInterval(async () => {
    let s;
    try {
      s = await api.fetchJob(job.jobId);
    } catch (e) {
      stopFill();
      filling.value = null;
      imgError.value = e.message;
      return;
    }
    filling.value = { done: s.done, total: s.total || job.total };
    ((s.result && s.result.images) || []).forEach(applyImage);
    if (s.status === "succeeded" || s.status === "failed") {
      stopFill();
      filling.value = null;
      if (s.status === "failed") imgError.value = s.error;
      api.discardJob(job.jobId).catch(() => {});   //图已经写进词库，任务行没用了
    }
  }, 2000);
}

function onKey(e) {
  if (e.key === "Escape") zoomed.value = null;
}
watch(zoomed, (word) => {
  if (word) window.addEventListener("keydown", onKey);
  else window.removeEventListener("keydown", onKey);
});
onBeforeUnmount(() => window.removeEventListener("keydown", onKey));
</script>

<template>
  <main v-if="family" class="enter">
    <div class="famhead">
      <div class="kicker" lang="en">{{ family.kind === 'theme' ? 'theme' : 'root' }} · {{ family.family }}</div>
      <div v-if="family.kind === 'theme'" class="root">
        <span class="tag">主题</span><span class="zh">{{ family.rootMeaning }}</span></div>
      <div v-else class="root" lang="en">{{ family.root }}<span class="eq">=</span>
        <span class="zh">{{ family.rootMeaning }}</span></div>
      <p class="intro">{{ family.intro }}</p>
      <div class="stats">
        <div><b>{{ family.learned }} / {{ family.total }}</b>已学过</div>
        <div v-if="family.nextDate"><b>{{ human(family.nextDate) }}</b>下次回来</div>
        <div v-if="family.source === 'agent'"><b>Agent</b>智能体生成</div>
      </div>
    </div>

    <h2>这一族的词</h2>
    <p class="muted note-lead">每行都带词根拆解，点一下展开联想、例句和简笔画。</p>
    <div class="wordlist">
      <WordCard v-for="w in family.words" :key="w.word" :word="w"
                :root="family.kind === 'theme' ? '' : family.root"
                :drawing="drawing === w.word" @draw="drawOne(w.word)"
                @zoom="zoomed = $event" />
    </div>

    <div class="actionbar">
      <button class="big" type="button" :disabled="state.busy" @click="start(freshCount ? 'fresh' : 'all')">
        {{ freshCount ? `开始：先学 ${freshCount} 个新词` : "整族重过一遍" }}
      </button>
      <div class="row">
        <button v-if="family.learned" class="btn" type="button" :disabled="state.busy" @click="start('due')">只练到期</button>
        <button v-if="family.learned" class="btn" type="button" :disabled="state.busy" @click="start('weak')">练习不熟</button>
        <button class="btn ghost" type="button" @click="router.push({ name: 'home' })">← 便签墙</button>
      </div>
      <div class="row">
        <button v-if="missingImgs" class="btn" type="button" :disabled="!!filling || !!drawing"
                @click="fillFamily">
          <span v-if="filling" class="spinner" aria-hidden="true"></span>
          {{ filling ? `正在画 ${filling.done}/${filling.total}` : `把剩下的 ${missingImgs} 张图一次画齐` }}
        </button>
        <p v-if="imgError" class="check bad">{{ imgError }}</p>
      </div>
    </div>
  </main>

  <main v-else-if="missing" class="enter">
    <div class="card"><div class="muted">找不到这个词族。</div></div>
    <div class="row">
      <button class="btn ghost" type="button" @click="router.push({ name: 'home' })">← 回便签墙</button>
    </div>
  </main>

  <Teleport to="body">
    <div v-if="zoomed" class="lightbox" @click.self="zoomed = null">
      <figure>
        <img :src="zoomed.img" width="1024" height="1024" decoding="async"
             :alt="zoomed.imgZh || zoomed.word + ' 的简笔画'">
        <figcaption v-if="zoomed.imgZh">{{ zoomed.imgZh }}</figcaption>
        <!-- 只有智能体画的图能重画；种子插画是手绘的，不给覆盖。 -->
        <div v-if="generated" class="row redraw">
          <button class="btn" type="button" :disabled="!!drawing" @click="drawOne(zoomed.word)">
            <span v-if="drawing" class="spinner" aria-hidden="true"></span>
            {{ drawing ? "正在重画……" : "不满意，重画一张" }}
          </button>
        </div>
        <p v-if="imgError" class="check bad">{{ imgError }}</p>
      </figure>
    </div>
  </Teleport>
</template>
