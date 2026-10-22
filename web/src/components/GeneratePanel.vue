<script setup>
import { computed, onBeforeUnmount, ref, watch } from "vue";
import * as api from "../api";

const props = defineProps({ open: { type: Boolean, default: false } });
const emit = defineEmits(["close", "created", "need-settings"]);

// input → grouping → pick → staging → preview → saving → saved
const stage = ref("input");
const text = ref("");
const error = ref("");
const groups = ref([]);      // 第一步的分组结果
const ungrouped = ref([]);
const picked = ref([]);      // 分组阶段勾中的下标
const results = ref([]);     // 第二步暂存好的完整词族
const chosen = ref([]);      // 预览阶段勾中的下标
const saved = ref([]);
const jobId = ref("");       // 暂存任务号，关掉面板时要通知后端丢掉
const progress = ref({ done: 0, total: 0 });
let timer = null;

const running = computed(() => stage.value === "grouping" || stage.value === "staging");
const saving = computed(() => stage.value === "saving");
const busy = computed(() => running.value || saving.value);
const ready = computed(() => text.value.trim().length >= 2);
const needKey = computed(() => error.value.includes("密钥"));
const busyLabel = computed(() =>
  stage.value === "grouping" ? "智能体正在分组"
    : `智能体正在逐族生成，${progress.value.done}/${progress.value.total}`);

function stop() {
  if (timer) clearInterval(timer);
  timer = null;
}
onBeforeUnmount(stop);

function reset() {
  stop();
  stage.value = "input";
  error.value = "";
  groups.value = [];
  ungrouped.value = [];
  picked.value = [];
  results.value = [];
  chosen.value = [];
  saved.value = [];
  jobId.value = "";
  progress.value = { done: 0, total: 0 };
}

// 不要这批内容：让后端把暂存一起删掉，词库里什么都不留。
function drop() {
  const id = jobId.value;
  if (id) api.discardJob(id).catch(() => {});
  reset();
}

// 关掉面板就等于不要这批内容：通知后端删掉暂存，词库里什么都不留。
function close() {
  if (busy.value || (stage.value === "preview" && chosen.value.length)) {
    const what = busy.value ? "生成还没跑完" : "这批词族还没加进便签墙";
    if (!confirm(`${what}，现在关掉就全丢了，也不作缓存。确定关掉吗？`)) return;
  }
  const id = jobId.value;
  stop();
  if (id) api.discardJob(id).catch(() => {});
  reset();
  emit("close");
}

function onKey(e) {
  if (e.key === "Escape" && !busy.value) close();
}
watch(() => props.open, (open) => {
  if (open) window.addEventListener("keydown", onKey);
  else window.removeEventListener("keydown", onKey);
});
onBeforeUnmount(() => window.removeEventListener("keydown", onKey));

function fail(message) {
  stage.value = "input";
  error.value = message || "生成失败";
  progress.value = { done: 0, total: 0 };
}

function poll(id, onEnd) {
  stop();
  timer = setInterval(async () => {
    let s;
    try {
      s = await api.fetchJob(id);
    } catch (e) {
      stop();
      return fail(e.message);
    }
    if (s.total) progress.value = { done: s.done, total: s.total };
    if (s.result && s.result.results) results.value = s.result.results;
    if (s.status === "succeeded" || s.status === "failed") {
      stop();
      onEnd(s);
    }
  }, 2500);
}

// 第一步：只分组，便宜，先让用户挑要哪几族，再去生成完整内容。
async function submit() {
  if (busy.value || !ready.value) return;
  error.value = "";
  results.value = [];
  groups.value = [];
  progress.value = { done: 0, total: 0 };
  stage.value = "grouping";
  try {
    const job = await api.startGrouping({ text: text.value, maxFamilies: 6 });
    poll(job.jobId, (s) => {
      api.discardJob(job.jobId).catch(() => {});   //分组结果已经拿到手，任务行不用留着
      if (s.status !== "succeeded") return fail(s.error);
      groups.value = s.result.groups;
      ungrouped.value = s.result.ungrouped;
      picked.value = s.result.groups.map((g, i) => i);
      if (!groups.value.length) {
        return fail(ungrouped.value.length
          ? `这几个词凑不成一族：${ungrouped.value.join("、")}`
          : "没分出可用的词族，换一批词试试");
      }
      stage.value = "pick";
    });
  } catch (e) {
    fail(e.message);
  }
}

// 第二步：把勾中的族生成完整内容，暂存在任务行里，还没进词库。
async function generatePicked() {
  const wanted = groups.value.filter((g, i) => picked.value.includes(i));
  if (!wanted.length || busy.value) return;
  error.value = "";
  results.value = [];
  progress.value = { done: 0, total: wanted.length };
  stage.value = "staging";
  try {
    const job = await api.startBatch(wanted.map((g) => ({
      root: g.root, rootMeaning: g.rootMeaning, kind: g.kind, words: g.words,
    })));
    jobId.value = job.jobId;
    poll(job.jobId, (s) => {
      results.value = (s.result && s.result.results) || [];
      if (!results.value.length) return fail(s.error);
      chosen.value = results.value.map((r, i) => (r.ok ? i : -1)).filter((i) => i >= 0);
      error.value = s.status === "failed" ? s.error : "";
      stage.value = "preview";
    });
  } catch (e) {
    fail(e.message);
  }
}

// 第三步：用户点了「加入便签墙」，这一步才真的写进词库。
async function savePicked() {
  if (!jobId.value || !chosen.value.length || saving.value) return;
  error.value = "";
  stage.value = "saving";
  try {
    const data = await api.saveGenerated(jobId.value, chosen.value);
    saved.value = data.saved;
    jobId.value = "";
    stage.value = "saved";
    if (data.skipped.length) error.value = data.skipped.map((s) => s.error).join("；");
    emit("created", null);
  } catch (e) {
    fail(e.message);
  }
}

function toggleGroup(i) {
  picked.value = picked.value.includes(i) ? picked.value.filter((x) => x !== i) : [...picked.value, i];
}

function togglePick(i) {
  chosen.value = chosen.value.includes(i) ? chosen.value.filter((x) => x !== i) : [...chosen.value, i];
}

function goSettings() {
  close();
  emit("need-settings");
}
</script>

<template>
  <div v-show="open" class="dialog" @click.self="close">
    <div class="panel" role="dialog" aria-modal="true" aria-label="新增词族">
      <button class="close" type="button" aria-label="关闭" @click="close">
        <svg viewBox="0 0 20 20" width="17" height="17" fill="none" stroke="currentColor"
             stroke-width="1.9" stroke-linecap="round" aria-hidden="true">
          <path d="M5 5l10 10M15 5L5 15" />
        </svg>
      </button>

      <form class="gen" @submit.prevent="submit">
        <h2>新增词族</h2>

        <template v-if="stage === 'input'">
          <p class="muted">把要记的词直接写进来，或者只写一个词根。同词根的串成一族，
            不同词根的自动分成几族，串不起词根的按它们的联系凑成主题族。</p>
          <textarea v-model="text" :disabled="busy" spellcheck="false" aria-label="要处理的单词或词根"
                    placeholder="同词根：inspect respect prospect spectator&#10;不同词根：inspect export conduct dictionary&#10;串不起词根：apple reluctant threshold&#10;只给词根：spect"></textarea>
          <div class="row">
            <button class="btn" type="submit" :disabled="busy || !ready">让智能体分一分</button>
          </div>
        </template>

        <p v-if="running" class="status">
          <span class="spinner" aria-hidden="true"></span>{{ busyLabel }}，一族大约半分钟。
        </p>

        <template v-if="stage === 'pick'">
          <p class="muted">分成 {{ groups.length }} 族，默认全要，不想要的点掉，再生成完整内容。</p>
          <div class="grouplist">
            <button v-for="(g, i) in groups" :key="g.root + i" type="button" class="groupitem"
                    :aria-pressed="picked.includes(i)" @click="toggleGroup(i)">
              <span class="tickbox" aria-hidden="true">
                <svg viewBox="0 0 20 20" width="13" height="13" fill="none" stroke="currentColor"
                     stroke-width="2.6" stroke-linecap="round" stroke-linejoin="round">
                  <path d="M4 10.5l4 4 8-9" />
                </svg>
              </span>
              <span class="gi-main">
                <span class="gi-root">
                  <template v-if="g.kind === 'theme'">主题 · {{ g.rootMeaning }}</template>
                  <template v-else-if="g.words.length"><span lang="en">{{ g.root }}</span><span class="eq">=</span>{{ g.rootMeaning }}</template>
                  <template v-else>词根 <span lang="en">{{ g.root }}</span></template>
                </span>
                <span class="gi-why">{{ g.why || "让智能体挑这一族最常见的词" }}</span>
                <span v-if="g.words.length" class="gi-words">
                  <span v-for="w in g.words" :key="w" lang="en">{{ w }}</span>
                </span>
              </span>
            </button>
          </div>
          <p v-if="ungrouped.length" class="ungrouped">
            实在凑不成一组的词：{{ ungrouped.join('、') }}
          </p>
          <div class="row">
            <button class="btn ghost" type="button" @click="drop">重新输入</button>
            <button class="btn" type="button" :disabled="!picked.length" @click="generatePicked">
              生成选中的 {{ picked.length }} 族
            </button>
          </div>
        </template>

        <template v-if="stage === 'preview' || stage === 'saving'">
          <p class="muted">内容都写好了，还没进词库。勾中的才会挂上便签墙，其余的关掉就丢。</p>
          <div class="grouplist">
            <div v-for="(r, i) in results" :key="r.root + i" class="famcard"
                 :class="{ off: r.ok && !chosen.includes(i), bad: !r.ok }">
              <button v-if="r.ok" class="groupitem fchead" type="button" :disabled="saving"
                      :aria-pressed="chosen.includes(i)" @click="togglePick(i)">
                <span class="tickbox" aria-hidden="true">
                  <svg viewBox="0 0 20 20" width="13" height="13" fill="none" stroke="currentColor"
                       stroke-width="2.6" stroke-linecap="round" stroke-linejoin="round">
                    <path d="M4 10.5l4 4 8-9" />
                  </svg>
                </span>
                <span class="gi-main">
                  <span class="gi-root">
                    <template v-if="r.kind === 'theme'">主题 · {{ r.rootMeaning }}</template>
                    <template v-else><span lang="en">{{ r.root }}</span><span class="eq">=</span>{{ r.rootMeaning }}</template>
                  </span>
                  <span class="gi-why">{{ r.family.intro }}</span>
                </span>
              </button>
              <p v-else class="fcfail"><b lang="en">{{ r.root }}</b>{{ r.error }}</p>
              <ul v-if="r.ok" class="fcwords">
                <li v-for="w in r.family.words" :key="w.word">
                  <span class="fw-top"><b lang="en">{{ w.word }}</b><i>{{ w.pos }}</i>{{ w.gloss }}</span>
                  <span class="fw-part" lang="en">{{ w.part }}</span>
                  <span class="fw-meme">{{ w.meme }}</span>
                </li>
              </ul>
              <p v-if="r.ok && r.dupes && r.dupes.length" class="fcdupes">
                已经在词库里，这次没重复生成：{{ r.dupes.join('、') }}
              </p>
            </div>
          </div>
          <div class="row">
            <button class="btn ghost" type="button" :disabled="saving" @click="drop">都不要</button>
            <button class="btn" type="button" :disabled="saving || !chosen.length" @click="savePicked">
              {{ saving ? "正在挂上墙……" : `加入便签墙（${chosen.length} 族）` }}
            </button>
          </div>
        </template>

        <template v-if="stage === 'saved'">
          <div class="grouplist">
            <div v-for="s in saved" :key="s.familyId" class="jobline ok">
              <span class="jroot" lang="en">{{ s.root }}</span>
              <span class="jmsg">已挂上便签墙（{{ s.words }} 个词）</span>
              <button class="mini" type="button" @click="emit('created', s.familyId)">去看</button>
            </div>
          </div>
          <p v-if="!saved.length" class="status">这次没有新增词族。</p>
          <div class="row">
            <button class="btn ghost" type="button" @click="reset">再来一批</button>
            <button class="btn" type="button" @click="close">关闭</button>
          </div>
        </template>

        <p v-if="error" class="status bad">{{ error }}</p>
        <div class="row" v-if="needKey">
          <button class="btn" type="button" @click="goSettings">去设置里填密钥</button>
        </div>
      </form>
    </div>
  </div>
</template>
