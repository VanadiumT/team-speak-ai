<template>
  <div class="error-display">
    <div class="error-icon">❌</div>
    <div class="error-message">{{ error }}</div>
  </div>
</template>

<script setup>
defineProps({
  error: { type: String, default: '未知错误' },
})
</script>

<style scoped>
.error-display {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 10px;
  padding: 30px;
  text-align: center;
}
.error-icon { font-size: 2rem; }
.error-message { color: #f44336; font-size: 0.95rem; }
</style>
