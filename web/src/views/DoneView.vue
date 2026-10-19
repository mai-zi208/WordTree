<script setup>
import { computed, onMounted } from "vue";
import { useRouter } from "vue-router";
import { human, state } from "../store";
import { say } from "../say";

const router = useRouter();
const summary = computed(() => state.summary);

const line = computed(() => {
  const s = summary.value;
  if (!s) return "明天见";
  if (s.familyRoot) return `${s.familyRoot} 这一族 ${human(s.nextDate) || "很快"} 回来`;
  return s.nextDate ? `最近一个词 ${human(s.nextDate)} 回来` : "下一批词明天回来";
});

onMounted(() => {
  if (summary.value) say(`${summary.value.items} 题做完了。${line.value}`);
});
</script>

<template>
  <main v-if="summary" class="enter">
    <div class="card done">
      <div class="d1">{{ summary.items }} 题做完了</div>
      <div class="d2">{{ line }}</div>
      <div v-if="summary.rolledBackRoots.length" class="warn2">
        {{ summary.rolledBackRoots.join("、") }} 忘了三个以上，整族已降回短间隔：忘的不是那个词，是族内联系还没搭起来。
      </div>
      <button class="big" type="button" @click="router.push({ name: 'home' })">回便签墙</button>
    </div>
  </main>
</template>
