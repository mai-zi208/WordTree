<script setup>
const RATES = [
  { k: "fast", label: "秒对", note: "+1 档" },
  { k: "back", label: "想起来了", note: "+1 档" },
  { k: "long", label: "想了很久", note: "不变" },
  { k: "gone", label: "完全忘了", note: "从头再来" },
];

defineProps({ pressed: { type: String, default: "" } });
defineEmits(["rate"]);
</script>

<template>
  <h2 id="ratelabel">你刚才是什么感觉？</h2>
  <div class="rate" role="group" aria-labelledby="ratelabel">
    <button v-for="r in RATES" :key="r.k" type="button" class="btn"
            :class="{ 'r-gone': r.k === 'gone' }" :aria-pressed="String(pressed === r.k)"
            @click="$emit('rate', r.k)">
      {{ r.label }}<small>{{ r.note }}</small>
    </button>
  </div>
</template>
