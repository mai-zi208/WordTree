<script setup>
import { computed, onBeforeUnmount, ref, watch } from "vue";
import * as api from "../api";

const props = defineProps({ open: { type: Boolean, default: false } });
const emit = defineEmits(["close", "created", "need-settings"]);

const mode = ref("book");
const stage = ref("input");
const text = ref("");
const keyword = ref("");
const error = ref("");
const groups = ref([]);
const ungrouped = ref([]);
const picked = ref([]);
const results = ref([]);
const progress = ref({ done: 0, total: 0 });
let timer = null;

const running = computed(() => stage.value === "running");
const ready = computed(() =>
  mode.value === "book" ? text.value.trim().length >= 2 : !!keyword.value.trim());
const needKey = computed(() => error.value.includes("密钥"));
const busyLabel = computed(() => {
  if (progress.value.total) return `智能体正在逐族生成，${progress.value.done}/${progress.value.total}`;
  return mode.value === "book" ? "智能体正在按词根分组" : "智能体正在写这一族";
});

function stop() {
  if (timer) clearInterval(timer);
  timer = null;
}
onBeforeUnmount(stop);

// 用 v-show 而不是 v-if：关掉弹层时任务还在跑，重新打开要能看到进度。
function onKey(e) {
  if (e.key === "Escape" && !running.value) emit("close");
}
watch(() => props.open, (open) => {
  if (open) window.addEventListener("keydown", onKey);
  else window.removeEventListener("keydown", onKey);
});
onBeforeUnmount(() => window.removeEventListener("keydown", onKey));

function fail(message) {
  stage.value = "failed";
  error.value = message || "生成失败";
  progress.value = { done: 0, total: 0 };
}

function poll(jobId, onEnd) {
  stop();
  timer = setInterval(async () => {
    let s;
    try {
      s = await api.fetchJob(jobId);
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

function switchMode(next) {
  if (running.value || mode.value === next) return;
  mode.value = next;
  reset();
}

function reset() {
  stop();
  stage.value = "input";
  error.value = "";
  groups.value = [];
  ungrouped.value = [];
  picked.value = [];
  results.value = [];
  progress.value = { done: 0, total: 0 };
}

async function submit() {
  if (running.value || !ready.value) return;
  error.value = "";
  results.value = [];
  progress.value = { done: 0, total: 0 };
  stage.value = "running";
  try {
    if (mode.value === "root") {
      const job = await api.startGeneration(keyword.value.trim());
      poll(job.jobId, (s) => {
        if (s.status !== "succeeded") return fail(s.error);
        keyword.value = "";
        stage.value = "done";
        emit("created", s.familyId);
      });
      return;
    }
    const job = await api.startGrouping({ text: text.value, maxFamilies: 6 });
    poll(job.jobId, (s) => {
      if (s.status !== "succeeded") return fail(s.error);
      groups.value = s.result.groups;
      ungrouped.value = s.result.ungrouped;
      picked.value = s.result.groups.map((g) => g.root);
      stage.value = groups.value.length ? "preview" : "failed";
      if (!groups.value.length) error.value = "没分出可用的词族，换一批词试试";
    });
  } catch (e) {
    fail(e.message);
  }
}

async function generatePicked() {
  const chosen = groups.value
    .filter((g) => picked.value.includes(g.root))
    .map((g) => ({ root: g.root, words: g.words }));
  if (!chosen.length || running.value) return;
  error.value = "";
  results.value = [];
  progress.value = { done: 0, total: chosen.length };
  stage.value = "running";
  try {
    const job = await api.startBatch(chosen);
    poll(job.jobId, (s) => {
      results.value = (s.result && s.result.results) || [];
      stage.value = "done";
      if (s.status === "failed" && !results.value.some((r) => r.ok)) error.value = s.error;
      emit("created", null);
    });
  } catch (e) {
    fail(e.message);
  }
}

function toggle(root) {
  picked.value = picked.value.includes(root)
    ? picked.value.filter((r) => r !== root)
    : [...picked.value, root];
}

function goSettings() {
  emit("close");
  emit("need-settings");
}
</script>

<template>
  <div v-show="open" class="dialog" @click.self="emit('close')">
    <div class="panel" role="dialog" aria-modal="true" aria-label="新增词族">
      <button class="close" type="button" aria-label="关闭" @click="emit('close')">
        <svg viewBox="0 0 20 20" width="17" height="17" fill="none" stroke="currentColor"
             stroke-width="1.9" stroke-linecap="round" aria-hidden="true">
          <path d="M5 5l10 10M15 5L5 15" />
        </svg>
      </button>

      <form class="gen" @submit.prevent="submit">
        <h2>新增词族</h2>

        <div class="tabs" role="tablist" aria-label="添词族的方式">
          <button type="button" role="tab" :aria-selected="mode === 'book'" :disabled="running"
                  @click="switchMode('book')">粘贴词本</button>
          <button type="button" role="tab" :aria-selected="mode === 'root'" :disabled="running"
                  @click="switchMode('root')">给个词根</button>
        </div>

        <template v-if="stage === 'input' || stage === 'failed'">
          <template v-if="mode === 'book'">
            <p class="muted">把词本或课本单元的单词粘进来，一行一个、逗号隔开都行，中文释义可以留着。
              智能体先按词根分组给你过目，勾选之后再逐族写联想和例句。</p>
            <textarea v-model="text" :disabled="running" spellcheck="false" aria-label="词本内容"
                      placeholder="inspect v. 检查&#10;respect n. 尊重&#10;prospect n. 前景&#10;spectator n. 观众&#10;perspective n. 视角"></textarea>
          </template>
          <template v-else>
            <p class="muted">给一个词根（比如 duct、mit、cred），选词、联想、例句都交给智能体，
              校验通过才进词库。</p>
            <div class="field">
              <input v-model="keyword" type="text" maxlength="40" placeholder="词根" aria-label="词根"
                     :disabled="running" lang="en">
              <button class="mini" type="submit" :disabled="running || !ready">生成</button>
            </div>
          </template>
          <div class="row" v-if="mode === 'book'">
            <button class="btn" type="submit" :disabled="running || !ready">让智能体分组</button>
          </div>
        </template>

        <p v-if="running" class="status">
          <span class="spinner" aria-hidden="true"></span>{{ busyLabel }}，一族大约半分钟。
        </p>

        <template v-if="stage === 'preview'">
          <p class="muted">分出 {{ groups.length }} 族，勾选要的，再一次性生成。</p>
          <div class="grouplist">
            <button v-for="g in groups" :key="g.root" type="button" class="groupitem"
                    :aria-pressed="picked.includes(g.root)" @click="toggle(g.root)">
              <span class="tickbox" aria-hidden="true">
                <svg viewBox="0 0 20 20" width="13" height="13" fill="none" stroke="currentColor"
                     stroke-width="2.6" stroke-linecap="round" stroke-linejoin="round">
                  <path d="M4 10.5l4 4 8-9" />
                </svg>
              </span>
              <span class="gi-main">
                <span class="gi-root" lang="en">{{ g.root }}<span class="eq">=</span>{{ g.rootMeaning }}</span>
                <span class="gi-why">{{ g.why }}</span>
                <span class="gi-words">
                  <span v-for="w in g.words" :key="w" lang="en">{{ w }}</span>
                </span>
              </span>
            </button>
          </div>
          <p v-if="ungrouped.length" class="ungrouped">
            没凑成族的词：{{ ungrouped.join('、') }}（可以单独用「给个词根」再试）
          </p>
          <div class="row">
            <button class="btn ghost" type="button" @click="reset">重选词表</button>
            <button class="btn" type="button" :disabled="!picked.length" @click="generatePicked">
              生成选中的 {{ picked.length }} 族
            </button>
          </div>
        </template>

        <template v-if="stage === 'done'">
          <div v-if="results.length" class="grouplist">
            <div v-for="r in results" :key="r.root" class="jobline" :class="r.ok ? 'ok' : 'bad'">
              <span class="jroot" lang="en">{{ r.root }}</span>
              <span class="jmsg">
                <template v-if="r.ok">已进词库（{{ r.words.length }} 个词）</template>
                <template v-else>{{ r.error }}</template>
              </span>
              <button v-if="r.ok" class="mini" type="button" @click="emit('created', r.familyId)">
                去看
              </button>
            </div>
          </div>
          <p v-else class="status ok">新词族已经挂到便签墙上了。</p>
          <div class="row">
            <button class="btn ghost" type="button" @click="reset">再来一批</button>
            <button class="btn" type="button" @click="emit('close')">关闭</button>
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
