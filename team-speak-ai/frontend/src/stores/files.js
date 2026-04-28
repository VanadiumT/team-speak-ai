/**
 * Files Store — 基于 WebSocket 的文件上传进度跟踪
 */

import { defineStore } from 'pinia'
import { ref } from 'vue'
import { pipelineSocket } from '@/api/pipeline.js'

export const useFilesStore = defineStore('files', () => {
  const uploads = ref({})

  function onUploadProgress({ upload_id, received, total }) {
    uploads.value[upload_id] = {
      ...uploads.value[upload_id],
      upload_id, received, total, status: 'uploading',
    }
  }

  function onUploadDone({ upload_id, file_id, name, size }) {
    uploads.value[upload_id] = { upload_id, file_id, name, size, received: size, total: size, status: 'done' }
  }

  function onUploadError({ upload_id, error }) {
    uploads.value[upload_id] = { ...uploads.value[upload_id], upload_id, status: 'error', error }
  }

  function init() {
    pipelineSocket.on('file.upload_progress', onUploadProgress)
    pipelineSocket.on('file.upload_done', onUploadDone)
    pipelineSocket.on('file.upload_error', onUploadError)
  }

  return { uploads, init }
})
