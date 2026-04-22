import axios from 'axios'

const apiClient = axios.create({
  baseURL: '/api',
  timeout: 30000,
})

export const uploadFile = (file, functionId, batchId = null) => {
  const formData = new FormData()
  formData.append('file', file)
  formData.append('function_id', functionId)
  if (batchId) formData.append('batch_id', batchId)

  return apiClient.post('/files/upload', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })
}

export const uploadBatch = (files, functionId, metadata = {}) => {
  const formData = new FormData()
  files.forEach((file) => formData.append('files', file))
  formData.append('function_id', functionId)
  formData.append('metadata', JSON.stringify(metadata))

  return apiClient.post('/files/upload/batch', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })
}

export const getBatch = (batchId) => apiClient.get(`/files/batch/${batchId}`)

export const getFile = (fileId) => apiClient.get(`/files/${fileId}`)

export const getFileContent = (fileId) => apiClient.get(`/files/${fileId}/content`)

export const deleteBatch = (batchId) => apiClient.delete(`/files/batch/${batchId}`)

export const deleteFile = (fileId) => apiClient.delete(`/files/${fileId}`)
