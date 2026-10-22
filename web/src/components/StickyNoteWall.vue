<script setup>
import { computed } from "vue";
import { human, wallOrder } from "../store";

const props = defineProps({ families: { type: Array, required: true } });
defineEmits(["open"]);

const STAGE_LABEL = { fresh: "还没开始", part: "学了一部分", done: "全学完了" };

// 一排挂在同一根线上的卡片歪得各不相同，才像吊着的便签而不是表格。
// 长度跟卡片张数互质，上下相邻两张不会撞同一个角度。
const TILT = [-0.8, 0.6, -0.4, 0.9, -0.6, 0.3, -1.0, 0.5];

// 没学过的排前面、学过的排后面，顺序由 store 的 wallOrder 统一给：
// 词族页的「上一族/下一族」走的是同一个顺序，两边必须一致。
const shown = computed(() => wallOrder(props.families));

function stage(f) {
  if (!f.learned) return "fresh";
  return f.learned >= f.total ? "done" : "part";
}
</script>

<template>
  <div class="wall">
    <button
      v-for="(f, i) in shown"
      :key="f.id"
      type="button"
      class="note"
      :class="`s-${stage(f)}`"
      :style="{ '--rot': `${TILT[i % TILT.length]}deg` }"
      :aria-label="f.kind === 'theme'
        ? `打开主题「${f.rootMeaning}」，${STAGE_LABEL[stage(f)]}，${f.total} 个词已学 ${f.learned} 个`
        : `打开 ${f.root} 词族，${STAGE_LABEL[stage(f)]}，${f.total} 个词已学 ${f.learned} 个`"
      @click="$emit('open', f.id)"
    >
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
