<template>
  <div class="audio-player">
    <div class="audio-info" v-if="audioSize">
      🔊 音频已生成 ({{ formatSize(audioSize) }})
    </div>
    <div v-else class="audio-info empty">无音频数据</div>
  </div>
</template>

<script setup>
defineProps({
  audioSize: { type: Number, default: 0 },
})

const formatSize = (bytes) => {
  if (bytes < 1024) return bytes + ' B'
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB'
  return (bytes / (1024 * 1024)).toFixed(1) + ' MB'
}
</script>

<style scoped>
.audio-player {
  padding: 20px;
  text-align: center;
}
.audio-info {
  color: #4caf50;
  font-size: 1rem;
}
.audio-info.empty { color: #555; }
</style>
