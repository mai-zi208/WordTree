<script setup>
import { computed, ref, watch } from "vue";
import { useRouter } from "vue-router";
import QuestionCard from "../components/QuestionCard.vue";
import RatePanel from "../components/RatePanel.vue";
import { commitSession, rate, state } from "../store";
import { say } from "../say";

const router = useRouter();

const items = computed(() => state.session?.items ?? []);
const index = computed(() => state.session?.index ?? 0);
const item = computed(() => items.value[index.value] || null);

const asked = ref(false);
const picked = ref(-1);
const placed = ref([]);
const correct = ref(false);
const pressed = ref("");

watch(item, () => {
  asked.value = false;
  picked.value = -1;
  placed.value = [];
  correct.value = false;
  pressed.value = "";
});

const placedText = computed(() => placed.value.map((i) => item.value?.chips[i] ?? "").join(" "));
const progress = computed(() =>
  items.value.length ? Math.round((index.value / items.value.length) * 100) : 0
);

function pick(oi) {
  if (asked.value || !item.value) return;
  picked.value = oi;
  asked.value = true;
  correct.value = item.value.options[oi] === item.value.answer;
  say(`${correct.value ? "答对了。" : `答错了，正确答案是 ${item.value.answer}。`}请选一下刚才的感觉。`);
}

function place(ci) {
  if (asked.value || !item.value || placed.value.includes(ci)) return;
  placed.value = [...placed.value, ci];
  if (placed.value.length === item.value.chips.length) {
    asked.value = true;
    correct.value = placedText.value === item.value.answer;
    say(correct.value ? "拼对了。" : `拼错了，答案是 ${item.value.answer}。`);
  }
}

function unplace(si) {
  if (asked.value) return;
  placed.value = placed.value.filter((_, i) => i !== si);
}

async function onRate(key) {
  if (!item.value || state.busy) return;
  pressed.value = key;
  rate(item.value.word, key);
  if (state.session && state.session.index >= items.value.length) {
    const summary = await commitSession();
    router.push({ name: summary ? "done" : "home" });
  }
}
</script>

<template>
  <main v-if="item" class="enter">
    <div class="qhead">
      <h1>{{ state.session.mode === "review" ? "复习" : "练习" }}</h1>
      <span class="count" lang="en">{{ index + 1 }} / {{ items.length }}</span>
    </div>
    <div class="bar" role="progressbar" :aria-valuenow="index" aria-valuemin="0"
         :aria-valuemax="items.length" aria-label="本题进度">
      <i :style="{ width: `${progress}%` }"></i>
    </div>

    <QuestionCard :item="item" :asked="asked" :picked="picked" :placed="placed" :correct="correct"
                  @pick="pick" @place="place" @unplace="unplace" />

    <RatePanel v-if="asked" :pressed="pressed" @rate="onRate" />
  </main>
</template>
