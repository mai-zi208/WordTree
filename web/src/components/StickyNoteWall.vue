<script setup>
import { nextTick, onBeforeUnmount, onMounted, ref, watch } from "vue";
import { human } from "../store";

const props = defineProps({ families: { type: Array, required: true } });
defineEmits(["open"]);

const NOTE_BG = ["var(--n1)", "var(--n2)", "var(--n3)"];
const NOTE_PIN = ["#a4472f", "#2e7d57", "#3f5fa0"];

const wall = ref(null);
const svg = ref(null);
const d = ref("");

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
  const pts = notes.map((n) => ({ x: n.offsetLeft + 22, y: n.offsetTop + 22 }));
  pts.unshift({ x: -8, y: pts[0].y - 6 });
  pts.push({ x: w + 8, y: pts[pts.length - 1].y - 6 });
  let path = `M${pts[0].x} ${pts[0].y}`;
  for (let i = 1; i < pts.length; i += 1) {
    const a = pts[i - 1];
    const b = pts[i];
    const mx = (a.x + b.x) / 2;
    path += ` C${mx} ${a.y} ${mx} ${b.y} ${b.x} ${b.y}`;
  }
  d.value = path;
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
      :aria-label="`打开 ${f.root} 词族，${f.total} 个词，已学 ${f.learned} 个`"
      @click="$emit('open', f.id)"
    >
      <span class="pin" :style="{ '--pin': NOTE_PIN[i % NOTE_PIN.length] }"></span>
      <span class="sheet" :style="{ background: NOTE_BG[i % NOTE_BG.length] }">
        <span class="root">{{ f.root }}<span class="eq">=</span>{{ f.rootMeaning }}</span>
        <span class="members">
          <span v-for="w in f.words" :key="w.word" lang="en">{{ w.word }}</span>
        </span>
        <span class="meta">
          <span class="stages" aria-hidden="true">
            <i v-for="n in 7" :key="n" :class="{ on: n <= f.stageSum }"></i>
          </span>
          <template v-if="f.learned">
            {{ f.learned }}/{{ f.total }} 已学<template v-if="f.nextDate">　·　下次 {{ human(f.nextDate) }}</template>
          </template>
          <template v-else>还没开始</template>
          <span v-if="f.source === 'agent'" class="agentpill">Agent</span>
          <span v-else-if="!f.learned" class="newpill">NEW</span>
        </span>
      </span>
    </button>
  </div>
</template>
