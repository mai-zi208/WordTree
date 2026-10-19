<script setup>
import { onMounted } from "vue";
import { state, loadFamilies } from "./store";

onMounted(loadFamilies);

function retry() {
  state.error = "";
  loadFamilies();
}
</script>

<template>
  <div class="notice" v-if="state.error" role="alert">
    <div class="banner">
      <span>{{ state.error }}</span>
      <button class="retry" type="button" @click="retry">重试</button>
    </div>
  </div>
  <RouterView />
</template>
