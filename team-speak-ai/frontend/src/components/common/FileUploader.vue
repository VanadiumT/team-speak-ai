<template>
  <div class="file-uploader">
    <div
      class="drop-zone"
      :class="{ 'drag-over': isDragOver }"
      @drop.prevent="handleDrop"
      @dragover.prevent="isDragOver = true"
      @dragleave="isDragOver = false"
      @click="openFileDialog"
    >
      <input
        ref="fileInput"
        type="file"
        :accept="accept"
        :multiple="multiple"
        @change="handleFileSelect"
        hidden
      />
      <div class="upload-icon">📁</div>
      <div class="upload-text">{{ dropText }}</div>
    </div>

    <div v-if="files.length > 0" class="file-list">
      <div v-for="file in files" :key="file.name" class="file-item">
        <span class="file-icon">{{ getFileIcon(file) }}</span>
        <span class="file-name">{{ file.name }}</span>
        <span class="file-meta">{{ formatSize(file.size) }}</span>
        <button @click.stop="removeFile(file)" class="remove-btn">✕</button>
      </div>
    </div>

    <div class="actions">
      <button @click="uploadFiles" :disabled="files.length === 0 || uploading">
        {{ uploading ? '上传中...' : '上传' }}
      </button>
      <button @click="clearFiles" :disabled="files.length === 0">清空</button>
    </div>

    <div v-if="uploadResult" class="upload-result" :class="uploadResult.status">
      {{ uploadResult.message }}
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { useFilesStore } from '@/stores/files'

const props = defineProps({
  functionId: { type: String, required: true },
  batchId: { type: String, default: null },
  accept: { type: String, default: 'image/*' },
  multiple: { type: Boolean, default: true },
})

const filesStore = useFilesStore()

const fileInput = ref(null)
const isDragOver = ref(false)
const files = ref([])
const uploading = ref(false)
const uploadResult = ref(null)

const dropText = computed(() => {
  if (isDragOver.value) return '放开以上传'
  return '拖拽文件到这里，或点击选择'
})

const openFileDialog = () => {
  fileInput.value?.click()
}

const handleFileSelect = (event) => {
  const selectedFiles = Array.from(event.target.files)
  addFiles(selectedFiles)
  event.target.value = ''
}

const handleDrop = (event) => {
  isDragOver.value = false
  const droppedFiles = Array.from(event.dataTransfer.files)
  addFiles(droppedFiles)
}

const addFiles = (newFiles) => {
  newFiles.forEach((file) => {
    if (!files.value.find((f) => f.name === file.name && f.size === file.size)) {
      files.value.push(file)
    }
  })
}

const removeFile = (file) => {
  files.value = files.value.filter(
    (f) => !(f.name === file.name && f.size === file.size)
  )
}

const clearFiles = () => {
  files.value = []
  uploadResult.value = null
}

const uploadFiles = async () => {
  if (files.value.length === 0) return

  uploading.value = true
  uploadResult.value = null

  try {
    const result = await filesStore.uploadBatch(files.value, props.functionId)
    uploadResult.value = {
      status: 'success',
      message: `上传成功！批次ID: ${result.batch_id}`,
    }
    clearFiles()
  } catch (error) {
    uploadResult.value = {
      status: 'error',
      message: `上传失败: ${error.message || '未知错误'}`,
    }
  } finally {
    uploading.value = false
  }
}

const getFileIcon = (file) => {
  if (file.type.startsWith('image/')) return '🖼️'
  if (file.type.startsWith('video/')) return '🎬'
  if (file.type.startsWith('audio/')) return '🎵'
  if (file.type.includes('pdf')) return '📄'
  if (file.type.includes('zip') || file.type.includes('rar')) return '📦'
  return '📎'
}

const formatSize = (bytes) => {
  if (bytes < 1024) return bytes + ' B'
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB'
  return (bytes / (1024 * 1024)).toFixed(1) + ' MB'
}
</script>

<style scoped>
.file-uploader {
  max-width: 600px;
}

.drop-zone {
  border: 2px dashed #0f3460;
  border-radius: 12px;
  padding: 40px 20px;
  text-align: center;
  cursor: pointer;
  transition: all 0.2s;
  background: #16213e;
}

.drop-zone:hover,
.drop-zone.drag-over {
  border-color: #e94560;
  background: rgba(233, 69, 96, 0.1);
}

.upload-icon {
  font-size: 3rem;
  margin-bottom: 10px;
}

.upload-text {
  color: #888;
  font-size: 0.9rem;
}

.file-list {
  margin-top: 20px;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.file-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 15px;
  background: #16213e;
  border-radius: 8px;
}

.file-icon {
  font-size: 1.2rem;
}

.file-name {
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.file-meta {
  color: #888;
  font-size: 0.85rem;
}

.remove-btn {
  background: none;
  border: none;
  color: #888;
  cursor: pointer;
  font-size: 1rem;
  padding: 5px;
}

.remove-btn:hover {
  color: #f44336;
}

.actions {
  margin-top: 20px;
  display: flex;
  gap: 10px;
}

.actions button {
  padding: 10px 25px;
  border: none;
  border-radius: 8px;
  cursor: pointer;
  font-size: 1rem;
  transition: all 0.2s;
}

.actions button:first-child {
  background: #e94560;
  color: white;
}

.actions button:first-child:hover:not(:disabled) {
  background: #d63850;
}

.actions button:last-child {
  background: #0f3460;
  color: #eaeaea;
}

.actions button:hover:not(:disabled) {
  opacity: 0.9;
}

.actions button:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.upload-result {
  margin-top: 15px;
  padding: 12px;
  border-radius: 8px;
  font-size: 0.9rem;
}

.upload-result.success {
  background: rgba(76, 175, 80, 0.2);
  color: #4caf50;
}

.upload-result.error {
  background: rgba(244, 67, 54, 0.2);
  color: #f44336;
}
</style>
