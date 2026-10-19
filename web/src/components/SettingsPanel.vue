<script setup>
import { onBeforeUnmount, ref, watch } from "vue";
import * as api from "../api";

const props = defineProps({ open: { type: Boolean, default: false } });
const emit = defineEmits(["close", "saved"]);

const baseUrl = ref("");
const model = ref("");
const apiKey = ref("");
const current = ref(null);
const check = ref(null);
const busy = ref(false);
const error = ref("");

async function load() {
  error.value = "";
  check.value = null;
  try {
    current.value = await api.fetchSettings();
    baseUrl.value = current.value.baseUrl;
    model.value = current.value.model;
    apiKey.value = "";
  } catch (e) {
    error.value = e.message;
  }
}

async function save(verify) {
  if (busy.value) return;
  busy.value = true;
  error.value = "";
  check.value = null;
  try {
    const payload = { baseUrl: baseUrl.value.trim(), model: model.value.trim(), verify };
    if (apiKey.value.trim()) payload.apiKey = apiKey.value.trim();
    current.value = await api.saveSettings(payload);
    apiKey.value = "";
    check.value = current.value.check || null;
    emit("saved", current.value);
  } catch (e) {
    error.value = e.message;
  } finally {
    busy.value = false;
  }
}

function onKey(e) {
  if (e.key === "Escape") emit("close");
}
watch(() => props.open, (open) => {
  if (open) {
    load();
    window.addEventListener("keydown", onKey);
  } else {
    window.removeEventListener("keydown", onKey);
  }
});
onBeforeUnmount(() => window.removeEventListener("keydown", onKey));
</script>

<template>
  <div v-if="open" class="dialog" @click.self="$emit('close')">
    <div class="panel" role="dialog" aria-modal="true" aria-label="模型与密钥设置">
      <h2>模型与密钥</h2>
      <p class="muted">填一次就存进 <code>backend/.env</code>，后端立刻生效，不用重启。
        这个文件已经被 git 忽略，密钥不会上传。</p>

      <div class="fieldrow">
        <label for="set-url">接口地址</label>
        <input id="set-url" v-model="baseUrl" type="text" lang="en" spellcheck="false"
               placeholder="https://api.deepseek.com" :disabled="busy">
        <p class="note">任何 OpenAI 兼容接口都行，末尾不用带 <code>/chat/completions</code>。</p>
      </div>

      <div class="fieldrow">
        <label for="set-model">模型名</label>
        <input id="set-model" v-model="model" type="text" lang="en" spellcheck="false"
               placeholder="deepseek-chat" :disabled="busy">
      </div>

      <div class="fieldrow">
        <label for="set-key">API 密钥</label>
        <input id="set-key" v-model="apiKey" type="password" lang="en" spellcheck="false"
               autocomplete="off" :placeholder="current && current.keyHint
                 ? `已存好（${current.keyHint}），留空表示不改` : '还没配置'" :disabled="busy">
        <p class="note">保存后只显示尾号，接口不会把密钥回传前端。</p>
      </div>

      <div class="row">
        <button class="btn" type="button" :disabled="busy" @click="save(false)">只保存</button>
        <button class="btn" type="button" :disabled="busy" @click="save(true)">保存并测试</button>
      </div>

      <p v-if="busy" class="check"><span class="spinner" aria-hidden="true"></span>正在试连……</p>
      <p v-else-if="check" class="check" :class="check.ok ? 'ok' : 'bad'">{{ check.message }}</p>
      <p v-else-if="error" class="check bad">{{ error }}</p>
      <p v-else-if="current" class="check" :class="current.configured ? 'ok' : 'bad'">
        {{ current.configured ? `当前可用：${current.model}` : "当前没有密钥，生成词族会失败" }}
      </p>

      <div class="row">
        <button class="btn ghost" type="button" @click="$emit('close')">关闭</button>
      </div>
    </div>
  </div>
</template>
