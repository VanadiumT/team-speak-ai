/**
 * Files Store 测试 — 仅测试公开 API
 */

import { describe, it, expect, vi, beforeEach } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'

vi.mock('@/api/pipeline', () => ({
  pipelineSocket: {
    on: vi.fn(),
    off: vi.fn(),
    sendCommand: vi.fn().mockResolvedValue({}),
    connected: false,
  },
}))

import { useFilesStore } from '../files'

describe('FilesStore', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
  })

  it('初始状态', () => {
    const store = useFilesStore()
    expect(store.uploads).toEqual({})
    expect(store.hasActiveUploads).toBe(false)
    expect(store.completedFiles).toEqual([])
  })

  it('registerUpload 注册上传', () => {
    const store = useFilesStore()
    store.registerUpload('upl_001', { fileName: 'test.wav', fileSize: 1024 })
    expect(store.uploads.upl_001).toBeDefined()
    expect(store.uploads.upl_001.status).toBe('uploading')
    expect(store.uploads.upl_001.fileName).toBe('test.wav')
    expect(store.uploads.upl_001.fileSize).toBe(1024)
    expect(store.hasActiveUploads).toBe(true)
  })

  it('registerUpload 多个上传', () => {
    const store = useFilesStore()
    store.registerUpload('upl_001', { fileName: 'a.wav', fileSize: 100 })
    store.registerUpload('upl_002', { fileName: 'b.wav', fileSize: 200 })
    expect(Object.keys(store.uploads)).toHaveLength(2)
  })

  it('markError 标记错误', () => {
    const store = useFilesStore()
    store.registerUpload('upl_001', { fileName: 'test.wav', fileSize: 100 })
    store.markError('upl_001', '上传失败')
    expect(store.uploads.upl_001.status).toBe('error')
    expect(store.uploads.upl_001.error).toBe('上传失败')
    expect(store.hasActiveUploads).toBe(false)
  })

  it('markError 不存在的 upload 忽略', () => {
    const store = useFilesStore()
    store.markError('nonexist', 'error')  // 不应抛异常
  })

  it('getUploadByNodeId 按节点查找', () => {
    const store = useFilesStore()
    store.registerUpload('upl_001', { nodeId: 'n1', fileName: 'a.wav', fileSize: 100 })
    store.registerUpload('upl_002', { nodeId: 'n2', fileName: 'b.wav', fileSize: 200 })
    const found = store.getUploadByNodeId('n1')
    expect(found?.upload_id).toBe('upl_001')
    expect(found?.fileName).toBe('a.wav')
  })

  it('getUploadByNodeId 未找到返回 null', () => {
    const store = useFilesStore()
    expect(store.getUploadByNodeId('nonexist')).toBeNull()
  })

  it('getUploadByNodeId 同节点返回最新的', () => {
    const store = useFilesStore()
    store.registerUpload('upl_001', { nodeId: 'n1', fileName: 'old.wav', fileSize: 100 })
    store.registerUpload('upl_002', { nodeId: 'n1', fileName: 'new.wav', fileSize: 200 })
    const found = store.getUploadByNodeId('n1')
    expect(found?.upload_id).toBe('upl_002')
  })

  it('clearCompleted 清除已完成', () => {
    const store = useFilesStore()
    store.registerUpload('upl_001', { fileName: 'a.wav', fileSize: 100 })
    store.registerUpload('upl_002', { fileName: 'b.wav', fileSize: 200 })
    // 手动设置状态
    store.uploads.upl_001.status = 'done'
    store.clearCompleted()
    expect(store.uploads.upl_001).toBeUndefined()
    expect(store.uploads.upl_002).toBeDefined()
  })

  it('clearCompleted 保留非完成状态', () => {
    const store = useFilesStore()
    store.registerUpload('upl_001', { fileName: 'a.wav', fileSize: 100 })
    store.markError('upl_001', '失败')
    store.clearCompleted()
    expect(store.uploads.upl_001).toBeDefined()
  })

  it('completedFiles 计算属性', () => {
    const store = useFilesStore()
    store.registerUpload('upl_001', { fileName: 'a.wav', fileSize: 100 })
    store.registerUpload('upl_002', { fileName: 'b.wav', fileSize: 200 })
    store.uploads.upl_001.status = 'done'
    expect(store.completedFiles).toHaveLength(1)
    expect(store.completedFiles[0].upload_id).toBe('upl_001')
  })
})
