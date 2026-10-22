<script setup>
import { nextTick, onBeforeUnmount, onMounted, ref, watch } from "vue";
import { human } from "../store";

const props = defineProps({ families: { type: Array, required: true } });
defineEmits(["open"]);

const COLS = 4;
const NOTE_PIN = ["#a4472f", "#2e7d57", "#3f5fa0"];
const STAGE_LABEL = { fresh: "还没开始", part: "学了一部分", done: "全学完了" };

// 每张卡片自己的歪斜和偏移，让整面墙像随手贴上去的而不是排版排出来的。
// 三个数组的长度互质，也跟 4 列互质，所以同一列上下几张不会重样。
const TILT = [-1.4, 0.8, -0.5, 1.5, -1.1, 0.6, -1.5, 1.0, -0.7, 1.3, -0.9];
const NUDGE_X = [0, -2, 1.5, -1, 2, -1.5, 0.5];
const NUDGE_Y = [0, 5, -3, 6, -1, 3, -5, 2, 4, -2];

function nudge(i) {
  return { x: NUDGE_X[i % NUDGE_X.length], y: NUDGE_Y[i % NUDGE_Y.length] };
}

// 蛇形靠 grid 定位实现，DOM 顺序保持词库顺序：藤蔓按 DOM 连线才是一条不断的蛇，
// 键盘 Tab 的顺序也跟视觉走向一致。
function cell(i) {
  const row = Math.floor(i / COLS);
  const col = i % COLS;
  return { gridRow: row + 1, gridColumn: row % 2 ? COLS - col : col + 1 };
}

function noteStyle(i) {
  const n = nudge(i);
  return { ...cell(i), "--rot": `${TILT[i % TILT.length]}deg`, "--dx": `${n.x}px`, "--dy": `${n.y}px` };
}

function stage(f) {
  if (!f.learned) return "fresh";
  return f.learned >= f.total ? "done" : "part";
}

const wall = ref(null);
const svg = ref(null);
const d = ref("");

// 藤蔓两头各伸出一段藏进端头的卡片背后；方向顺着蛇走，折返行的尾巴是往回伸的。
function vine(pts) {
  const dir = (a, b) => Math.sign(b.x - a.x) || 1;
  const last = pts[pts.length - 1];
  const all = [
    { x: pts[0].x - dir(pts[0], pts[1] || { x: pts[0].x + 1 }) * 40, y: pts[0].y - 6 },
    ...pts,
    { x: last.x + dir(pts[pts.length - 2] || { x: last.x - 1 }, last) * 40, y: last.y - 6 },
  ];
  let path = `M${all[0].x} ${all[0].y}`;
  for (let i = 1; i < all.length; i += 1) {
    const a = all[i - 1];
    const b = all[i];
    const mx = (a.x + b.x) / 2;
    path += ` C${mx} ${a.y} ${mx} ${b.y} ${b.x} ${b.y}`;
  }
  return path;
}

function draw() {
  const box = wall.value;
  const el = svg.value;
  if (!box || !el) return;
  const notes = [...box.querySelectorAll(".note")];
  if (!notes.length) return;
  const w = box.clientWidth;
  const h = box.clientHeight;
  el.setAttribute("width", w);
  el.setAttribute("height", h);
  el.setAttribute("viewBox", `0 0 ${w} ${h}`);
  // offsetLeft/offsetTop 是网格里的位置，不含 transform，所以要把卡片自己的偏移加回去，
  // 藤蔓才落在图钉那一条线上。
  d.value = vine(notes.map((n, i) => {
    const g = nudge(i);
    return { x: n.offsetLeft + n.offsetWidth / 2 + g.x, y: n.offsetTop + 16 + g.y };
  }));
}

let observer = null;
onMounted(async () => {
  await nextTick();
  draw();
  observer = new ResizeObserver(draw);
  observer.observe(wall.value);
  window.addEventListener("resize", draw);
});
onBeforeUnmount(() => {
  observer?.disconnect();
  window.removeEventListener("resize", draw);
});
watch(() => props.families, async () => {
  await nextTick();
  draw();
}, { deep: true });
</script>

<template>
  <div class="wall" ref="wall">
    <svg class="string" ref="svg" aria-hidden="true"><path :d="d" /></svg>
    <button
      v-for="(f, i) in families"
      :key="f.id"
      type="button"
      class="note"
      :class="`s-${stage(f)}`"
      :style="noteStyle(i)"
      :aria-label="f.kind === 'theme'
        ? `打开主题「${f.rootMeaning}」，${STAGE_LABEL[stage(f)]}，${f.total} 个词已学 ${f.learned} 个`
        : `打开 ${f.root} 词族，${STAGE_LABEL[stage(f)]}，${f.total} 个词已学 ${f.learned} 个`"
      @click="$emit('open', f.id)"
    >
      <span class="pin" :style="{ '--pin': NOTE_PIN[i % NOTE_PIN.length] }"></span>
      <span class="sheet">
        <span class="root">
          <template v-if="f.kind === 'theme'"><span class="tag">主题</span>{{ f.rootMeaning }}</template>
          <template v-else><span lang="en">{{ f.root }}</span><span class="eq">=</span>{{ f.rootMeaning }}</template>
        </span>
        <span class="members">
          <span v-for="w in f.words" :key="w.word" lang="en">{{ w.word }}</span>
        </span>
        <span class="meta">
          <span class="stages" aria-hidden="true">
            <i v-for="n in 7" :key="n" :class="{ on: n <= f.stageSum }"></i>
          </span>
          <template v-if="f.learned">
            {{ f.learned }}/{{ f.total }} 已学<template v-if="f.nextDate">　·　{{ human(f.nextDate) }}</template>
          </template>
          <template v-else>还没开始</template>
          <span v-if="f.source === 'agent'" class="agentpill">Agent</span>
          <span v-else-if="!f.learned" class="newpill">NEW</span>
        </span>
      </span>
    </button>
  </div>
</template>
