<template>
  <div class="uploader">
    <div
      class="up-zone"
      :class="{ over: isDragOver }"
      @drop.prevent="handleDrop"
      @dragover.prevent="isDragOver = true"
      @dragleave="isDragOver = false"
      @click="openDialog"
    >
      <input ref="fileInput" type="file" :accept="accept" :multiple="false" @change="handleSelect" hidden />
      <span class="up-ico">📤</span>
      <span class="up-hint">{{ isDragOver ? '放开以上传' : '拖拽文件或点击选择' }}</span>
    </div>
    <div class="up-info" v-if="selectedFile">
      <span>{{ selectedFile.name }}</span>
      <span class="up-size">{{ fmt(selectedFile.size) }}</span>
    </div>
    <button v-if="selectedFile" class="up-btn" :disabled="uploading" @click="doUpload">
      {{ uploading ? '上传中...' : '上传' }}
    </button>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'

const props = defineProps({
  accept: { type: String, default: 'image/*' },
})

const emit = defineEmits(['upload'])

const fileInput = ref(null)
const isDragOver = ref(false)
const selectedFile = ref(null)
const uploading = ref(false)

const openDialog = () => fileInput.value?.click()

const handleSelect = (e) => {
  if (e.target.files.length > 0) selectedFile.value = e.target.files[0]
  e.target.value = ''
}

const handleDrop = (e) => {
  isDragOver.value = false
  if (e.dataTransfer.files.length > 0) selectedFile.value = e.dataTransfer.files[0]
}

const doUpload = () => {
  if (!selectedFile.value) return
  uploading.value = true
  emit('upload', selectedFile.value)
  setTimeout(() => { uploading.value = false }, 1000)
}

const fmt = (b) => {
  if (b < 1024) return b + ' B'
  return (b / 1024).toFixed(1) + ' KB'
}
</script>

<style scoped>
.uploader { }

.up-zone {
  border: 1.5px dashed rgba(148,163,184,0.1);
  border-radius: 8px; padding: 18px;
  text-align: center; cursor: pointer;
  transition: all 0.2s;
  display: flex; flex-direction: column; gap: 6px; align-items: center;
}
.up-zone:hover, .up-zone.over {
  border-color: rgba(233,69,96,0.3);
  background: rgba(233,69,96,0.04);
}
.up-ico { font-size: 1.4rem; opacity: 0.6; }
.up-hint { font-size: 0.7rem; color: rgba(255,255,255,0.25); }

.up-info {
  display: flex; justify-content: space-between; align-items: center;
  padding: 8px 10px; margin-top: 8px;
  background: rgba(255,255,255,0.02);
  border-radius: 6px;
  font-size: 0.7rem; color: rgba(255,255,255,0.5);
}
.up-size { font-size: 0.6rem; color: rgba(255,255,255,0.2); }

.up-btn {
  margin-top: 8px; width: 100%;
  padding: 7px 0;
  background: rgba(233,69,96,0.1);
  border: 1px solid rgba(233,69,96,0.2);
  border-radius: 6px;
  color: #e94560; font-size: 0.7rem; cursor: pointer;
  transition: all 0.15s;
}
.up-btn:hover { background: rgba(233,69,96,0.18); }
.up-btn:disabled { opacity: 0.3; cursor: not-allowed; }
</style>
