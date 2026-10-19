<script setup>
// 图片由后端 /assets 提供，绑成动态值，避免 Vite 把它当本地模块去解析。
const HERO_IMG = "/assets/header.png";
</script>

<template>
  <div class="hero">
    <img :src="HERO_IMG" width="1792" height="1024" decoding="async"
         alt="水彩插画：一株高茎幼苗被三叶草与小花环绕，右上方洒下阳光">
  </div>
  <div class="masthead">
    <h1>词根花园</h1>
    <p class="sub">同一个词根，长出不同方向的词。</p>
  </div>
</template>
