<script setup>
import { onBeforeUnmount, ref } from "vue";
import * as api from "../api";

const emit = defineEmits(["created"]);

const keyword = ref("");
const status = ref("idle");
const error = ref("");
let timer = null;

async function submit() {
  const word = keyword.value.trim();
  if (!word || status.value === "running") return;
  error.value = "";
  status.value = "running";
  try {
    const job = await api.startGeneration(word);
    timer = setInterval(async () => {
      try {
        const s = await api.fetchJob(job.jobId);
        if (s.status === "succeeded") {
          stop();
          status.value = "done";
          keyword.value = "";
          emit("created", s.familyId);
        } else if (s.status === "failed") {
          stop();
          status.value = "failed";
          error.value = s.error || "生成失败";
        }
      } catch (e) {
        stop();
        status.value = "failed";
        error.value = e.message;
      }
    }, 2500);
  } catch (e) {
    status.value = "failed";
    error.value = e.message;
  }
}

function stop() {
  if (timer) clearInterval(timer);
  timer = null;
}
onBeforeUnmount(stop);
</script>

<template>
  <form class="gen" @submit.prevent="submit">
    <h2>让智能体现编一族</h2>
    <p class="muted">给一个词根（比如 duct、mit、cred），路由层交给智能体：词族、联想、例句一次生成，校验通过才进词库。</p>
    <div class="field">
      <input v-model="keyword" type="text" maxlength="40" placeholder="词根" aria-label="词根"
             :disabled="status === 'running'" lang="en">
      <button class="mini" type="submit" :disabled="status === 'running' || !keyword.trim()">
        {{ status === "running" ? "生成中" : "生成" }}
      </button>
    </div>
    <p v-if="status === 'running'" class="status"><span class="spinner" aria-hidden="true"></span>
      智能体正在写这一族，大约半分钟。</p>
    <p v-else-if="status === 'done'" class="status ok">新生成的词族已经挂到便签墙上了。</p>
    <p v-else-if="status === 'failed'" class="status bad">{{ error }}</p>
  </form>
</template>
