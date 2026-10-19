<script setup>
import { computed, onMounted, ref, watch } from "vue";
import { useRouter } from "vue-router";
import MorphTree from "../components/MorphTree.vue";
import WordCard from "../components/WordCard.vue";
import * as api from "../api";
import { familyById, human, startSession, state } from "../store";

const props = defineProps({ id: { type: String, required: true } });
const router = useRouter();
const fallback = ref(null);
const missing = ref(false);

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
</script>

<template>
  <main v-if="family" class="enter">
    <div class="famhead">
      <div class="kicker" lang="en">root · {{ family.family }}</div>
      <div class="root" lang="en">{{ family.root }}<span class="eq">=</span>
        <span class="zh">{{ family.rootMeaning }}</span></div>
      <p class="intro">{{ family.intro }}</p>
      <div class="stats">
        <div><b>{{ family.learned }} / {{ family.total }}</b>已学过</div>
        <div v-if="family.nextDate"><b>{{ human(family.nextDate) }}</b>下次回来</div>
        <div v-if="family.source === 'agent'"><b>Agent</b>智能体生成</div>
      </div>
    </div>

    <h2>词族拆解</h2>
    <MorphTree :family="family" />

    <h2>逐词细看</h2>
    <WordCard v-for="w in family.words" :key="w.word" :word="w" />

    <button class="big" type="button" :disabled="state.busy" @click="start(freshCount ? 'fresh' : 'all')">
      {{ freshCount ? `开始：先学 ${freshCount} 个新词` : "整族重过一遍" }}
    </button>
    <div class="row" v-if="family.learned">
      <button class="btn" type="button" :disabled="state.busy" @click="start('due')">只练到期</button>
      <button class="btn" type="button" :disabled="state.busy" @click="start('weak')">练习不熟</button>
    </div>
    <div class="row">
      <button class="btn ghost" type="button" @click="router.push({ name: 'home' })">← 回便签墙</button>
    </div>
  </main>

  <main v-else-if="missing" class="enter">
    <div class="card"><div class="muted">找不到这个词族。</div></div>
    <div class="row">
      <button class="btn ghost" type="button" @click="router.push({ name: 'home' })">← 回便签墙</button>
    </div>
  </main>
</template>
