<script setup>
defineProps({ family: { type: Object, required: true } });

function chunks(part, root) {
  return part
    .split("+")
    .map((s) => s.trim())
    .filter(Boolean)
    .map((chunk) => {
      const sp = chunk.indexOf(" ");
      const morph = sp < 0 ? chunk : chunk.slice(0, sp);
      const gloss = sp < 0 ? "" : chunk.slice(sp + 1).trim();
      return { morph, gloss, isRoot: morph.replace(/-/g, "") === root };
    });
}
</script>

<template>
  <div class="card tree">
    <div class="rootbox" lang="en">{{ family.root }} = {{ family.rootMeaning }}</div>
    <div v-for="w in family.words" :key="w.word" class="branch">
      <div style="min-width:0">
        <div class="w" lang="en">{{ w.word }}<span class="gloss">{{ w.gloss }}</span></div>
        <div class="morphs">
          <template v-for="(c, ci) in chunks(w.part, family.root)" :key="c.morph + ci">
            <span v-if="ci" class="plus">+</span>
            <span class="morph" :class="{ root: c.isRoot }">{{ c.morph }}</span>
            <span v-if="c.gloss" class="mg">{{ c.gloss }}</span>
          </template>
        </div>
      </div>
    </div>
  </div>
</template>
