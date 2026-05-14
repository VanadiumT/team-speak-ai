/**
 * Files Store — 文件上传进度跟踪与队列管理
 */

import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { pipelineSocket } from '@/api/pipeline'

interface UploadEntry {
  upload_id: string
  node_id?: string
  fileName?: string
  fileSize?: number
  received: number
  total: number
  status: 'uploading' | 'done' | 'error'
  file_id: string | null
  error: string | null
}

export const useFilesStore = defineStore('files', () => {
  const uploads = ref<Record<string, UploadEntry>>({})

  const hasActiveUploads = computed(() =>
    Object.values(uploads.value).some(u => u.status === 'uploading')
  )

  const completedFiles = computed(() =>
    Object.values(uploads.value).filter(u => u.status === 'done')
  )

  function onUploadProgress({ upload_id, received, total }: Record<string, unknown>): void {
    const id = upload_id as string
    const existing = uploads.value[id]
    if (!existing) return
    uploads.value = {
      ...uploads.value,
      [id]: { ...existing, received: received as number, total: total as number, status: 'uploading' },
    }
  }

  function onUploadDone({ upload_id, file_id, name, size }: Record<string, unknown>): void {
    const id = upload_id as string
    const existing = uploads.value[id]
    const sz = (size as number) || existing?.fileSize || 0
    uploads.value = {
      ...uploads.value,
      [id]: {
        upload_id: id,
        node_id: existing?.node_id,
        fileName: (name as string) || existing?.fileName,
        fileSize: sz,
        received: sz,
        total: sz,
        status: 'done',
        file_id: file_id as string,
        error: null,
      },
    }
  }

  function registerUpload(uploadId: string, { nodeId, fileName, fileSize }: { nodeId?: string; fileName: string; fileSize: number }): void {
    uploads.value = {
      ...uploads.value,
      [uploadId]: {
        upload_id: uploadId,
        node_id: nodeId,
        fileName,
        fileSize,
        received: 0,
        total: fileSize,
        status: 'uploading',
        file_id: null,
        error: null,
      },
    }
  }

  function markError(uploadId: string, error: string): void {
    const existing = uploads.value[uploadId]
    if (!existing) return
    uploads.value = {
      ...uploads.value,
      [uploadId]: { ...existing, status: 'error', error: String(error) },
    }
  }

  function getUploadByNodeId(nodeId: string): UploadEntry | null {
    const matches = Object.values(uploads.value).filter(u => u.node_id === nodeId)
    return matches.length ? matches[matches.length - 1] : null
  }

  async function cancelUpload(uploadId: string): Promise<void> {
    try {
      await pipelineSocket.sendCommand('_system', 'file.upload_cancel', { upload_id: uploadId })
    } catch { /* ignore */ }
    const existing = uploads.value[uploadId]
    if (existing) {
      uploads.value = {
        ...uploads.value,
        [uploadId]: { ...existing, status: 'error', error: '已取消' },
      }
    }
  }

  function clearCompleted(): void {
    const remaining: Record<string, UploadEntry> = {}
    for (const [id, u] of Object.entries(uploads.value)) {
      if (u.status !== 'done') remaining[id] = u
    }
    uploads.value = remaining
  }

  let _initialized = false
  function init(): void {
    if (_initialized) return
    _initialized = true
    pipelineSocket.on('file.upload_progress', onUploadProgress)
    pipelineSocket.on('file.upload_done', onUploadDone)
  }

  return {
    uploads,
    hasActiveUploads,
    completedFiles,
    registerUpload,
    markError,
    getUploadByNodeId,
    cancelUpload,
    clearCompleted,
    init,
  }
})
