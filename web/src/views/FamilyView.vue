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
                :root="family.kind === 'theme' ? '' : family.root" @zoom="zoomed = $event" />
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
      </figure>
    </div>
  </Teleport>
</template>
