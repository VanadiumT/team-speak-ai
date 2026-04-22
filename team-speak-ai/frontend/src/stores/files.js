import { defineStore } from 'pinia'
import {
  uploadFile as apiUploadFile,
  uploadBatch as apiUploadBatch,
  getBatch as apiGetBatch,
  deleteBatch as apiDeleteBatch,
  deleteFile as apiDeleteFile,
} from '@/api/files'

export const useFilesStore = defineStore('files', {
  state: () => ({
    batches: {},
    currentBatchId: null,
    uploading: false,
  }),

  actions: {
    async uploadFile(file, functionId, batchId = null) {
      this.uploading = true
      try {
        const response = await apiUploadFile(file, functionId, batchId)
        const result = response.data

        if (!this.batches[result.batch_id]) {
          this.batches[result.batch_id] = { files: [], info: {} }
        }
        this.batches[result.batch_id].files.push(result)

        return result
      } finally {
        this.uploading = false
      }
    },

    async uploadBatch(files, functionId) {
      this.uploading = true
      try {
        const response = await apiUploadBatch(files, functionId)
        const result = response.data

        this.batches[result.batch_id] = {
          files: result.files,
          info: { batch_id: result.batch_id },
        }

        return result
      } finally {
        this.uploading = false
      }
    },

    async getBatch(batchId) {
      const response = await apiGetBatch(batchId)
      this.batches[batchId] = {
        files: response.data,
        info: { batch_id: batchId },
      }
      return response.data
    },

    async deleteBatch(batchId) {
      await apiDeleteBatch(batchId)
      delete this.batches[batchId]
    },

    async deleteFile(batchId, fileId) {
      await apiDeleteFile(fileId)
      if (this.batches[batchId]) {
        this.batches[batchId].files = this.batches[batchId].files.filter(
          (f) => f.file_id !== fileId
        )
      }
    },

    clearBatch(batchId) {
      delete this.batches[batchId]
    },
  },
})
