<script setup>
import { computed, ref } from "vue";

const props = defineProps({
  word: { type: Object, required: true },
  root: { type: String, default: "" },
});
const emit = defineEmits(["zoom"]);

const open = ref(false);

// "in- 往里 + spect 看" → 词素 chip 加义注，词根本身高亮。
const chunks = computed(() =>
  props.word.part
    .split("+")
    .map((s) => s.trim())
    .filter(Boolean)
    .map((chunk) => {
      const sp = chunk.indexOf(" ");
      const morph = sp < 0 ? chunk : chunk.slice(0, sp);
      const gloss = sp < 0 ? "" : chunk.slice(sp + 1).trim();
      return { morph, gloss, isRoot: !!props.root && morph.replace(/-/g, "") === props.root };
    })
);

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
  <div class="card wordrow" :class="{ open }">
    <button class="wrow-head" type="button" :aria-expanded="open"
            :aria-label="`${word.word}，${word.gloss}，${open ? '收起' : '展开'}联想与例句`"
            @click="open = !open">
      <span class="w" lang="en">{{ word.word }}</span>
      <span class="pos" lang="en">{{ word.pos }}</span>
      <span class="gl">{{ word.gloss }}</span>
      <img v-if="word.img" class="thumb" :src="word.img" width="1024" height="1024"
           loading="lazy" decoding="async" alt="">
      <svg class="chev" viewBox="0 0 20 20" fill="none" stroke="currentColor" stroke-width="2"
           stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
        <path d="M5 8l5 5 5-5" />
      </svg>
    </button>

    <div class="morphs wrow-morphs">
      <template v-for="(c, ci) in chunks" :key="c.morph + ci">
        <span v-if="ci" class="plus">+</span>
        <span class="morph" :class="{ root: c.isRoot }">{{ c.morph }}</span>
        <span v-if="c.gloss" class="mg">{{ c.gloss }}</span>
      </template>
    </div>

    <div v-if="open" class="wrow-body">
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
      <button v-if="word.img" class="platebtn" type="button"
              :aria-label="`放大 ${word.word} 的简笔画`" @click="emit('zoom', word)">
        <img :src="word.img" width="1024" height="1024" loading="lazy" decoding="async"
             :alt="word.imgZh || word.word + ' 的简笔画'">
        <span class="cap">{{ word.imgZh ? word.imgZh + '　·　' : '' }}点图看大图</span>
      </button>
    </div>
  </div>
</template>
