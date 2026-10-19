<script setup>
import { computed } from "vue";

const props = defineProps({
  item: { type: Object, required: true },
  asked: Boolean,
  picked: { type: Number, default: -1 },
  placed: { type: Array, default: () => [] },
  correct: Boolean,
});
defineEmits(["pick", "place", "unplace"]);

const placedText = computed(() => props.placed.map((i) => props.item.chips[i]).join(" "));
const holes = computed(() => props.item.tokens.length - props.placed.length);
const available = computed(() =>
  props.item.chips.map((chip, ci) => ({ chip, ci })).filter(({ ci }) => !props.placed.includes(ci))
);
</script>

<template>
  <div class="card">
    <div class="tag">{{ item.stem.tag }}</div>

    <img v-if="item.kind === 'picture'" class="quizimg" :src="item.stem.img" width="1024"
         height="1024" decoding="async" :alt="item.stem.imgAlt || '题目图片'">
    <div v-else-if="item.stem.word" class="qstem" lang="en">{{ item.stem.word }}</div>
    <div v-else-if="item.stem.text" class="qtext">{{ item.stem.text }}</div>

    <div v-if="item.stem.note" class="muted note-lead">{{ item.stem.note }}</div>

    <template v-if="item.kind === 'order'">
      <div class="slots" aria-label="已拼出的顺序">
        <button v-for="(ci, si) in placed" :key="'p' + si" type="button" class="chip placed"
                :aria-label="`移回 ${item.chips[ci]}`" :disabled="asked" @click="$emit('unplace', si)">
          {{ item.chips[ci] }}
        </button>
        <span v-for="n in holes" :key="'h' + n" class="chip hole" aria-hidden="true">·</span>
      </div>
      <div class="bank" aria-label="可选词块">
        <button v-for="{ chip, ci } in available" :key="'b' + ci" type="button" class="chip"
                lang="en" :disabled="asked" @click="$emit('place', ci)">{{ chip }}</button>
      </div>
    </template>

    <template v-else>
      <button v-for="(opt, oi) in item.options" :key="oi" type="button" class="opt"
              :class="{ right: asked && opt === item.answer,
                        missed: asked && oi === picked && opt !== item.answer }"
              :disabled="asked" @click="$emit('pick', oi)">
        <span class="key" aria-hidden="true">{{ String.fromCharCode(65 + oi) }}</span>
        <span class="txt" :lang="item.kind === 'gloss' ? null : 'en'">{{ opt }}
          <small v-if="asked && item.optionNotes" class="ogloss"
                 :lang="item.kind === 'gloss' ? 'en' : null">{{ item.optionNotes[oi] }}</small>
        </span>
        <svg v-if="asked && opt === item.answer" class="mark" viewBox="0 0 20 20" fill="none"
             stroke="currentColor" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round"
             aria-hidden="true"><path d="M4 10.5l4 4 8-9" /></svg>
        <svg v-else-if="asked && oi === picked" class="mark" viewBox="0 0 20 20" fill="none"
             stroke="currentColor" stroke-width="2.4" stroke-linecap="round" aria-hidden="true">
          <path d="M5 5l10 10M15 5L5 15" /></svg>
      </button>
    </template>
  </div>

  <div v-if="asked && item.kind === 'order'" class="card">
    <div class="tag">参考答案</div>
    <div class="ansnote"><b lang="en">{{ item.answer }}</b></div>
    <div v-if="item.zh" class="ansnote zh">{{ item.zh }}</div>
    <div class="ansnote muted mine">{{ correct ? "你拼对了。" : `你拼的是：${placedText}` }}</div>
  </div>
  <div v-else-if="asked" class="card">
    <div class="tag">正确答案 {{ item.answer }}</div>
    <div class="muted">{{ item.hint }}</div>
    <div v-if="item.zh" class="muted zhline">{{ item.zh }}</div>
  </div>
</template>
