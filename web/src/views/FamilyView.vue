<script>
// 只在本次会话的第一张词族页提一句滚轮手势。README §1 明令前端不存 localStorage，所以放在模块作用域。
let hintSeen = false;
</script>

<script setup>
import { computed, onBeforeUnmount, onMounted, ref, watch } from "vue";
import { useRouter } from "vue-router";
import WordCard from "../components/WordCard.vue";
import * as api from "../api";
import { familyById, human, neighborFamily, startSession, state, wallOrder } from "../store";
import { say } from "../say";

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
const filling = ref(null);   // 整族补图的进度 { done, total, familyId }
const imgError = ref("");
const showHint = ref(!hintSeen);
let fillTimer = null;
// 补图任务属于发起它的那一族：翻到别的族时，不能让别人的进度把这一族的按钮变成哑的。
const fillHere = computed(() =>
  filling.value && filling.value.familyId === family.value?.id ? filling.value : null);

async function resolve() {
  missing.value = false;
  if (family.value) return;
  try {
    fallback.value = await api.fetchFamily(props.id);
  } catch {
    missing.value = true;
  }
}

// 翻页换族时组件实例是复用的，上一族的临时状态不清就会跟过来：
// 孤儿大图既盖住页面又把滚轮一直锁死；fallback 跟着来会让 resolve() 直接早退，页面卡在旧族。
watch(() => props.id, () => {
  zoomed.value = null;
  drawing.value = "";
  imgError.value = "";
  fallback.value = null;
  hidePeek();
  acc = 0; dir = 0; spent = true;   // 刚落地这一页，这一次手势已经用掉了
  resolve();
});

/* ---------- 滚轮翻族：先把这一页读完，到边再往外推才换族 ---------- */

const EDGE = 1.5;          // 判断"已经在页顶/页底"的容差，maxScroll 可能是小数
const PEEK = 45;           // 往外推过这么多才浮出提示
const FLING = 200;         // 推满这么多才真的换族，正好两格 Windows 滚轮
const GESTURE_GAP = 250;   // 静默超过它算新的一次手势
const COOLDOWN = 600;      // 两次换族的最小间隔

let acc = 0, dir = 0, spent = false, lastAt = 0, coolUntil = 0, peekTimer = null;
const peek = ref(0);       // 0..1，驱动提示里那根进度线
const peekDir = ref(0);    // -1 上一族 / +1 下一族 / 0 收起

// 页码和翻页顺序都按墙上的那一套（wallOrder），跟便签墙看到的下一张保持一致。
const ordered = computed(() => wallOrder(state.families));
const famIndex = computed(() => ordered.value.findIndex((f) => f.id === family.value?.id));
const famTotal = computed(() => ordered.value.length);
const hasPrev = computed(() => !!neighborFamily(props.id, -1));
const hasNext = computed(() => !!neighborFamily(props.id, 1));

// 大图开着、请求在飞、这一族不在库里、总共只有一族——任何一种都不该让翻页插手。
function canPage() {
  return !!family.value && !zoomed.value && !state.busy && famTotal.value > 1 && famIndex.value >= 0;
}

// Firefox 的滚轮一格报 3「行」，不归一化就得滚七十格才换族；触控板捏合缩放是带 ctrlKey 的 wheel 事件。
function normalize(deltaY, mode) {
  if (mode === 1) return deltaY * 33;
  if (mode === 2) return deltaY * document.documentElement.clientHeight;
  return deltaY;
}

function hidePeek() {
  peek.value = 0;
  peekDir.value = 0;
}

// replace 不用 push：连翻几族之后浏览器后退的语义是回便签墙，不是把这这几页倒着走一遍。
function go(d) {
  const next = neighborFamily(props.id, d);
  if (!next) return false;
  hintSeen = true;
  showHint.value = false;
  router.replace({ name: "family", params: { id: String(next.id) } });
  const i = state.families.findIndex((f) => f.id === next.id);
  say(`第 ${i + 1} 族，${next.kind === "theme" ? next.rootMeaning : next.root}`);
  return true;
}

function fire(d) {
  acc = 0; dir = 0; spent = true;
  coolUntil = performance.now() + COOLDOWN;
  hidePeek();
  go(d);
}

function onWheel(e) {
  const now = performance.now();
  // 一次手势只许翻一族：翻完把这次手势吃掉，等到静默超过 GESTURE_GAP 才重新计数。
  // 这条是承重的——换族后 scrollBehavior 把人放到新页顶部，同一次手势的惯性尾巴
  // 立刻变成「在顶部往上推」＝上一族，不吃掉就会 A→B→A→B 来回弹。
  if (now - lastAt > GESTURE_GAP) { acc = 0; dir = 0; spent = false; }
  lastAt = now;
  if (!canPage() || spent || now < coolUntil || e.ctrlKey || e.metaKey || e.altKey) return hidePeek();
  const px = normalize(e.deltaY, e.deltaMode);
  if (!px) return hidePeek();
  const d = Math.sign(px);
  const max = document.documentElement.scrollHeight - document.documentElement.clientHeight;
  const y = window.scrollY;
  const outward = (y <= EDGE && d < 0) || (max - y <= EDGE && d > 0);
  // 往页内推永远只是正常滚；中途换了方向就重新攒，免得「到底→往回滚三格→再滚三格」攒出误翻。
  if (!outward || (dir && d !== dir)) { acc = 0; dir = 0; return hidePeek(); }
  // 到头了这一族就没得翻：什么都不演，也别给出「继续下滑」然后又不动。
  if (d > 0 ? !hasNext.value : !hasPrev.value) { spent = true; return hidePeek(); }
  dir = d;
  acc += Math.abs(px);
  // 边界不回弹：preventDefault 只在已经推不动的方向上调用，否则 Windows 会亮一圈蓝色过滚动光晕。
  e.preventDefault();
  if (acc >= PEEK) {
    peekDir.value = d;
    peek.value = Math.min(1, (acc - PEEK) / (FLING - PEEK));
  }
  clearTimeout(peekTimer);
  peekTimer = setTimeout(hidePeek, GESTURE_GAP);
  if (acc >= FLING) fire(d);
}

/* ---------- 手机：横扫切族。文档横向滚不动，所以跟上下滑零冲突 ---------- */

let touch = null;

function onTouchStart(e) {
  const t = e.touches[0];
  touch = t ? { x: t.clientX, y: t.clientY, at: performance.now() } : null;
}

function onTouchEnd(e) {
  const g = touch;
  const t = e.changedTouches[0];
  touch = null;
  if (!g || !t || !canPage()) return;
  const dx = t.clientX - g.x;
  const dy = t.clientY - g.y;
  // 只认又快又偏横的那一下：纵向分量必须远小于横向，否则就是用户在滚页面。
  if (performance.now() - g.at < 500 && Math.abs(dx) >= 70 && Math.abs(dx) >= 2.2 * Math.abs(dy)) {
    go(dx < 0 ? 1 : -1);
  }
}

onMounted(() => {
  window.addEventListener("wheel", onWheel, { passive: false });
  window.addEventListener("touchstart", onTouchStart, { passive: true });
  window.addEventListener("touchend", onTouchEnd, { passive: true });
  resolve();
});

function stopFill() {
  if (fillTimer) clearInterval(fillTimer);
  fillTimer = null;
}
onBeforeUnmount(() => {
  stopFill();
  clearTimeout(peekTimer);
  window.removeEventListener("wheel", onWheel);
  window.removeEventListener("touchstart", onTouchStart);
  window.removeEventListener("touchend", onTouchEnd);
});

// 画好一张就贴一张：直接改 store 里那个词对象，不用整库重拉。
// familyId 是发起任务那一族，用户中途翻页也得把图贴回它自己的族。
function applyImage(item, familyId) {
  const fam = familyById(familyId ?? family.value?.id);
  const target = fam && fam.words.find((w) => w.word === item.word);
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

// 整族补图走后台任务，一张一张画，轮询进度。
async function fillFamily() {
  if (fillHere.value || !family.value) return;
  imgError.value = "";
  let job;
  const jobFamilyId = family.value.id;
  try {
    job = await api.startFamilyImages(jobFamilyId);
  } catch (e) {
    imgError.value = e.message;
    return;
  }
  filling.value = { done: 0, total: job.total, familyId: jobFamilyId };
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
    filling.value = { done: s.done, total: s.total || job.total, familyId: jobFamilyId };
    ((s.result && s.result.images) || []).forEach((it) => applyImage(it, jobFamilyId));
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
      <!-- 翻页控件全部 absolute，多占一像素页高都会把「滚到底」的判定挪走。 -->
      <div v-if="famIndex >= 0 && famTotal > 1" class="famnav">
        <button class="backbtn" type="button" :disabled="!hasPrev || state.busy"
                aria-label="上一族" @click="go(-1)">
          <svg viewBox="0 0 20 20" width="15" height="15" fill="none" stroke="currentColor"
               stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
            <path d="M12.5 4l-6 6 6 6" />
          </svg>
        </button>
        <span class="count">{{ famIndex + 1 }} / {{ famTotal }}</span>
        <button class="backbtn" type="button" :disabled="!hasNext || state.busy"
                aria-label="下一族" @click="go(1)">
          <svg viewBox="0 0 20 20" width="15" height="15" fill="none" stroke="currentColor"
               stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
            <path d="M7.5 4l6 6-6 6" />
          </svg>
        </button>
      </div>
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
    <p class="muted note-lead">每行都带词根拆解，点一下展开联想、例句和简笔画。<template v-if="showHint">滚轮翻到页底再往下推一下，就换下一族。</template></p>
    <div class="wordlist">
      <WordCard v-for="w in family.words" :key="w.word" :word="w"
                :root="family.kind === 'theme' ? '' : family.root"
                :drawing="drawing === w.word" @draw="drawOne(w.word)"
                @zoom="zoomed = $event" />
    </div>

    <div class="actionbar">
      <div class="peek" :class="{ on: peekDir !== 0 }" :style="{ '--p': peek }" aria-hidden="true">
        {{ peekDir > 0 ? "继续下滑 · 下一族" : "继续上推 · 上一族" }}<i></i>
      </div>
      <button class="big" type="button" :disabled="state.busy" @click="start(freshCount ? 'fresh' : 'all')">
        {{ freshCount ? `开始：先学 ${freshCount} 个新词` : "整族重过一遍" }}
      </button>
      <div class="row">
        <button v-if="family.learned" class="btn" type="button" :disabled="state.busy" @click="start('due')">只练到期</button>
        <button v-if="family.learned" class="btn" type="button" :disabled="state.busy" @click="start('weak')">练习不熟</button>
        <button class="btn ghost" type="button" @click="router.push({ name: 'home' })">← 便签墙</button>
      </div>
      <div class="row">
        <button v-if="missingImgs" class="btn" type="button" :disabled="!!fillHere || !!drawing"
                @click="fillFamily">
          <span v-if="fillHere" class="spinner" aria-hidden="true"></span>
          {{ fillHere ? `正在画 ${fillHere.done}/${fillHere.total}` : `把剩下的 ${missingImgs} 张图一次画齐` }}
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
