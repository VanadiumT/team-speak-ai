/**
 * Files Store — 文件上传进度跟踪与队列管理
 *
 * 监听后端推送的 file.upload_progress / file.upload_done 事件，
 * 提供按节点查询上传状态、取消上传、清理已完成记录等功能。
 */

import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { pipelineSocket } from '@/api/pipeline.js'

export const useFilesStore = defineStore('files', () => {
  // ── 状态 ──────────────────────────────────────────────────────
  const uploads = ref({})

  // ── 计算属性 ──────────────────────────────────────────────────

  /** 当前是否有正在上传的文件 */
  const hasActiveUploads = computed(() =>
    Object.values(uploads.value).some(u => u.status === 'uploading')
  )

  /** 所有已完成的上传记录 */
  const completedFiles = computed(() =>
    Object.values(uploads.value).filter(u => u.status === 'done')
  )

  // ── WebSocket 事件处理 ────────────────────────────────────────

  function onUploadProgress({ upload_id, received, total }) {
    const existing = uploads.value[upload_id]
    if (!existing) return // 未注册的上传，忽略
    uploads.value = {
      ...uploads.value,
      [upload_id]: { ...existing, received, total, status: 'uploading' },
    }
  }

  function onUploadDone({ upload_id, file_id, name, size }) {
    const existing = uploads.value[upload_id] || {}
    uploads.value = {
      ...uploads.value,
      [upload_id]: {
        ...existing,
        upload_id,
        file_id,
        name: name || existing.fileName,
        size: size || existing.fileSize,
        received: size || existing.fileSize,
        total: size || existing.fileSize,
        status: 'done',
      },
    }
  }

  // ── 公开方法 ──────────────────────────────────────────────────

  /**
   * 注册一个新的上传任务（在 uploadFile 的 onReady 回调中调用）
   * @param {string} uploadId - 后端返回的 upload_id
   * @param {object} meta - { nodeId, fileName, fileSize }
   */
  function registerUpload(uploadId, { nodeId, fileName, fileSize }) {
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

  /**
   * 标记上传失败（由调用方在 catch 中调用）
   * @param {string} uploadId
   * @param {string} error
   */
  function markError(uploadId, error) {
    const existing = uploads.value[uploadId]
    if (!existing) return
    uploads.value = {
      ...uploads.value,
      [uploadId]: { ...existing, status: 'error', error: String(error) },
    }
  }

  /**
   * 按节点 ID 查询该节点的上传记录（最新一条）
   * @param {string} nodeId
   * @returns {object|null}
   */
  function getUploadByNodeId(nodeId) {
    const matches = Object.values(uploads.value).filter(u => u.node_id === nodeId)
    return matches.length ? matches[matches.length - 1] : null
  }

  /**
   * 取消上传
   * @param {string} uploadId
   */
  async function cancelUpload(uploadId) {
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

  /**
   * 清理所有已完成的上传记录
   */
  function clearCompleted() {
    const remaining = {}
    for (const [id, u] of Object.entries(uploads.value)) {
      if (u.status !== 'done') remaining[id] = u
    }
    uploads.value = remaining
  }

  // ── 初始化 ────────────────────────────────────────────────────

  let _initialized = false
  function init() {
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
