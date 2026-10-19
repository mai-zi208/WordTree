<script setup>
import { useRouter } from "vue-router";
import GeneratePanel from "../components/GeneratePanel.vue";
import HeroMasthead from "../components/HeroMasthead.vue";
import StickyNoteWall from "../components/StickyNoteWall.vue";
import { loadFamilies, resetProgress, startSession, state } from "../store";

const router = useRouter();

async function review() {
  if (await startSession({ mode: "review" })) router.push({ name: "quiz" });
}

function open(id) {
  router.push({ name: "family", params: { id } });
}

async function created(familyId) {
  await loadFamilies();
  if (familyId) open(familyId);
}

async function clear() {
  if (confirm("清空所有复习进度？词库本身不会丢。")) await resetProgress();
}
</script>

<template>
  <HeroMasthead />
  <main class="enter">
    <div class="tip" :class="{ idle: !state.dueTotal }">
      <template v-if="state.dueTotal">
        <span class="grow"><span class="due-n">{{ state.dueTotal }}</span>个词今天到期</span>
        <button class="mini" type="button" :disabled="state.busy" @click="review">开始复习</button>
      </template>
      <span v-else class="grow">今天没有要复习的词</span>
    </div>

    <p v-if="!state.loaded && !state.error" class="loading">正在读词库……</p>
    <StickyNoteWall v-else :families="state.families" @open="open" />

    <GeneratePanel @created="created" />

    <div class="row">
      <button class="btn ghost" type="button" @click="clear">清空进度</button>
    </div>
  </main>
</template>
