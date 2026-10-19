<script setup>
import { computed } from "vue";

const props = defineProps({ word: { type: Object, required: true } });

const parts = computed(() => {
  const { example, blank } = props.word;
  const out = [];
  let i = 0;
  while (i < example.length) {
    const idx = example.indexOf(blank, i);
    if (idx < 0) {
      out.push({ text: example.slice(i), hit: false });
      break;
    }
    if (idx > i) out.push({ text: example.slice(i, idx), hit: false });
    out.push({ text: example.slice(idx, idx + blank.length), hit: true });
    i = idx + blank.length;
  }
  return out.filter((p) => p.text);
});

const isProse = computed(() => props.word.content.type !== "sentence");
</script>

<template>
  <div class="card wordcard">
    <div class="head">
      <span class="stem" lang="en">{{ word.word }}</span>
      <span class="pos" lang="en">{{ word.pos }}</span>
      <span class="gl">{{ word.gloss }}</span>
    </div>
    <div class="meme">
      <svg viewBox="0 0 20 20" width="15" height="15" fill="none" stroke="currentColor"
           stroke-width="1.7" stroke-linecap="round" aria-hidden="true">
        <path d="M10 2.5a4.6 4.6 0 00-2.7 8.3v1.7h5.4V10.8A4.6 4.6 0 0010 2.5z" />
        <path d="M8.2 15.2h3.6M8.9 17.3h2.2" />
      </svg>
      <span>{{ word.meme }}</span>
    </div>
    <div v-if="!isProse" class="en" lang="en">
      <template v-for="(p, pi) in parts" :key="pi"><b v-if="p.hit">{{ p.text }}</b><template v-else>{{ p.text }}</template></template>
    </div>
    <p v-else class="prose" lang="en">{{ word.content.en }}</p>
    <div class="zh">{{ word.content.zh }}</div>
    <figure v-if="word.img" class="plate">
      <img :src="word.img" width="1024" height="1024" loading="lazy" decoding="async"
           :alt="word.imgZh || word.word + ' 的简笔画'">
      <figcaption v-if="word.imgZh">{{ word.imgZh }}</figcaption>
    </figure>
  </div>
</template>
