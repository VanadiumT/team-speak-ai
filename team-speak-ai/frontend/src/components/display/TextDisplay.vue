<template>
  <div class="text-display">
    <div v-if="reasoning" class="reasoning-block">
      <div class="reasoning-title">💭 思考过程</div>
      <div class="reasoning-text">{{ reasoning }}</div>
    </div>
    <div class="content-text" v-if="text">{{ text }}</div>
    <div v-else class="empty-text">无内容</div>
  </div>
</template>

<script setup>
defineProps({
  text: { type: String, default: '' },
  reasoning: { type: String, default: '' },
})
</script>

<style scoped>
.text-display { line-height: 1.6; }
.reasoning-block {
  background: #0f3460;
  border-left: 3px solid #ff9800;
  border-radius: 8px;
  padding: 15px;
  margin-bottom: 15px;
}
.reasoning-title { font-size: 0.85rem; color: #ff9800; margin-bottom: 8px; }
.reasoning-text { color: #aaa; font-size: 0.9rem; white-space: pre-wrap; }
.content-text {
  color: #eaeaea;
  font-size: 1rem;
  white-space: pre-wrap;
  word-break: break-word;
}
.empty-text { color: #555; font-style: italic; }
</style>
