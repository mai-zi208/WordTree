<script setup>
// 图片由后端 /assets 提供，绑成动态值，避免 Vite 把它当本地模块去解析。
const HERO_IMG = "/assets/header.png";

defineProps({ settingsOpen: { type: Boolean, default: false } });
defineEmits(["open-settings"]);
</script>

<template>
  <div class="hero">
    <img :src="HERO_IMG" width="1792" height="1024" decoding="async"
         alt="水彩插画：一株高茎幼苗被三叶草与小花环绕，右上方洒下阳光">
  </div>
  <div class="masthead">
    <div class="titles">
      <h1>词根花园</h1>
      <p class="sub">同一个词根，长出不同方向的词。</p>
    </div>
    <button class="gear" type="button" :class="{ on: settingsOpen }"
            :aria-expanded="settingsOpen" aria-label="模型与密钥设置"
            @click="$emit('open-settings')">
      <svg viewBox="0 0 20 20" width="18" height="18" fill="none" stroke="currentColor"
           stroke-width="1.6" stroke-linecap="round" aria-hidden="true">
        <circle cx="10" cy="10" r="3.1" />
        <path d="M10 1.9v2M10 16.1v2M18.1 10h-2M3.9 10h-2M15.7 4.3l-1.4 1.4M5.7 14.3l-1.4 1.4M15.7 15.7l-1.4-1.4M5.7 5.7L4.3 4.3" />
      </svg>
    </button>
  </div>
</template>
