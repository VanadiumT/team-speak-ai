<template>
  <div class="input-image-body">
    <!-- Flow Mode + detail tab: upload area or file info -->
    <template v-if="!editMode || activeTab === 'detail'">
      <!-- PENDING: upload prompt -->
      <div v-if="status === 'pending'" class="upload-zone" @click="triggerUpload">
        <span class="material-symbols-outlined upload-icon">upload_file</span>
        <span class="upload-text">点击或拖拽上传</span>
        <span class="upload-hint">PNG / JPG / WebP · 最大 10 MB</span>
      </div>

      <!-- PROCESSING: progress bar (优先显示 files store 实时进度) -->
      <div v-else-if="status === 'processing' || (uploadState && uploadState.status === 'uploading')" class="upload-progress">
        <span class="material-symbols-outlined spin-icon">sync</span>
        <span class="progress-label">上传中...</span>
        <div class="mini-bar">
          <div class="mini-bar-fill" :style="{ width: uploadPercent + '%' }" />
        </div>
        <span class="progress-pct">{{ uploadPercent }}%</span>
      </div>

      <!-- COMPLETED: file info -->
      <div v-else-if="status === 'completed'" class="file-info">
        <span class="material-symbols-outlined done-icon">check_circle</span>
        <span class="file-name">{{ data?.file_name || '已上传' }}</span>
        <span class="file-meta" v-if="data?.file_size">{{ formatSize(data.file_size) }}</span>
        <button class="reupload-btn" @click="triggerUpload">重新上传</button>
      </div>

      <!-- ERROR -->
      <div v-else-if="status === 'error'" class="error-msg">
        <span class="material-symbols-outlined">error</span>
        <span>上传失败</span>
      </div>

      <!-- Default pending state -->
      <div v-else class="upload-zone" @click="triggerUpload">
        <span class="material-symbols-outlined upload-icon">upload_file</span>
        <span class="upload-text">点击或拖拽上传</span>
      </div>
    </template>

    <!-- Edit Mode: config tab -->
    <template v-if="editMode && activeTab === 'config'">
      <NodeConfigForm
        :config="node.config || {}"
        :fields="configFields"
        :readonly="false"
        @update="onConfigUpdate"
      />
    </template>

    <!-- IO Data tab -->
    <template v-if="activeTab === 'io-data'">
      <NodeIODataView :outputs="outputPorts" />
    </template>

    <!-- IO管理 tab -->
    <template v-if="activeTab === 'io-mgmt' && editMode">
      <NodeIOMgmt :node="node" :edit-mode="editMode" :input-ports="inputPorts" :output-ports="outputPorts" @toggle-port="onTogglePort" />
    </template>

    <!-- Log tab (shared) -->
    <template v-if="activeTab === 'log'">
      <NodeLogView :logs="logs" />
    </template>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { useEditorStore } from '@/stores/editor'
import { useFilesStore } from '@/stores/files'
import NodeConfigForm from './NodeConfigForm.vue'
import NodeIODataView from './NodeIODataView.vue'
import NodeIOMgmt from './NodeIOMgmt.vue'
import NodeLogView from './NodeLogView.vue'

const props = defineProps({
  node: { type: Object, required: true },
  status: { type: String, default: 'pending' },
  activeTab: { type: String, default: 'detail' },
  editMode: { type: Boolean, default: false },
  summary: { type: String, default: '' },
  progress: { type: Number, default: null },
  data: { type: Object, default: () => ({}) },
  config: { type: Object, default: () => ({}) },
  logs: { type: Array, default: () => [] },
  inputPorts: { type: Array, default: () => [] },
  outputPorts: { type: Array, default: () => [] }
})

const editorStore = useEditorStore()
const filesStore = useFilesStore()

// 从 files store 获取当前节点的上传状态（实时进度）
const uploadState = computed(() => filesStore.getUploadByNodeId(props.node.id))
const uploadPercent = computed(() => {
  const u = uploadState.value
  if (u && u.total > 0) return Math.round((u.received / u.total) * 100)
  return Math.round((props.progress ?? 0) * 100)
})

const configFields = [
  { key: 'accepted_formats', label: '接受格式', type: 'checkbox-group', options: [
    { value: 'png', label: 'PNG' }, { value: 'jpg', label: 'JPG' }, { value: 'webp', label: 'WebP' }
  ]},
  { key: 'max_size_mb', label: '最大体积 (MB)', type: 'number', min: 1, max: 100, placeholder: '10' }
]

const ioRuntime = computed(() => ({
  outputs: {
    'img-out': props.data?.file_name ? `文件: ${props.data.file_name}` : '(无数据)',
    'trigger-out': props.status === 'completed' ? '✓ 已触发' : '(等待)'
  },
  lastExecution: props.data?._ts || ''
}))

function onConfigUpdate({ key, value }) {
  editorStore.updateConfigImmediate(props.node.id, { [key]: value })
}

function onTogglePort(portId, show) {
  const vis = new Set(props.node.config?._visible_ports || [])
  if (show) vis.add(portId); else vis.delete(portId)
  editorStore.updateConfigImmediate(props.node.id, { _visible_ports: [...vis] })
}

function triggerUpload() {
  const input = document.createElement('input')
  input.type = 'file'
  input.accept = 'image/png,image/jpeg,image/webp'
  input.onchange = async (e) => {
    const file = e.target.files?.[0]
    if (!file) return
    const { pipelineSocket } = await import('@/api/pipeline')
    let uploadId = null
    try {
      await pipelineSocket.uploadFile(editorStore.flowId, file, props.node.id, (id) => {
        uploadId = id
        filesStore.registerUpload(id, {
          nodeId: props.node.id,
          fileName: file.name,
          fileSize: file.size,
        })
      })
    } catch (err) {
      if (uploadId) filesStore.markError(uploadId, err.message || '上传失败')
    }
  }
  input.click()
}

function formatSize(bytes) {
  if (!bytes) return ''
  if (bytes < 1024) return bytes + ' B'
  if (bytes < 1048576) return (bytes / 1024).toFixed(1) + ' KB'
  return (bytes / 1048576).toFixed(1) + ' MB'
}
</script>

<style scoped>
.input-image-body { padding: 4px 0; }

.upload-zone {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 4px;
  padding: 16px 8px;
  border: 1px dashed #414754;
  border-radius: 6px;
  cursor: pointer;
  transition: border-color 0.2s;
}
.upload-zone:hover { border-color: #4edea3; }
.upload-icon { font-size: 28px; color: #4edea3; }
.upload-text { font-size: 11px; color: #c1c6d7; }
.upload-hint { font-size: 9px; color: #64748b; }

.upload-progress {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 11px;
  color: #adc7ff;
}
.spin-icon { font-size: 16px; animation: spin 1s linear infinite; }
@keyframes spin { to { transform: rotate(360deg); } }
.mini-bar { flex: 1; height: 3px; background: #31353d; border-radius: 2px; overflow: hidden; }
.mini-bar-fill { height: 100%; background: #adc7ff; border-radius: 2px; transition: width 0.3s; }
.progress-label { font-size: 10px; color: #8b90a0; }
.progress-pct { font-size: 10px; font-family: 'Space Grotesk', sans-serif; color: #adc7ff; }

.file-info {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 2px;
  padding: 8px 0;
}
.done-icon { font-size: 22px; color: #4edea3; }
.file-name { font-size: 11px; color: #e0e2ed; font-weight: 500; }
.file-meta { font-size: 9px; color: #64748b; }
.reupload-btn {
  margin-top: 4px;
  padding: 3px 10px;
  border-radius: 4px;
  border: 1px solid #414754;
  background: transparent;
  color: #8b90a0;
  font-size: 10px;
  cursor: pointer;
}
.reupload-btn:hover { color: #c1c6d7; border-color: #8b90a0; }

.error-msg {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 11px;
  color: #ffb4ab;
}
</style>
