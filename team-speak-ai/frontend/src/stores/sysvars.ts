/**
 * SysVars Store — 系统变量管理
 */

import { defineStore } from 'pinia'
import { ref, reactive } from 'vue'
import { pipelineSocket } from '@/api/pipeline'

export const useSysVarsStore = defineStore('sysvars', () => {
  const vars = ref<Record<string, unknown>>({})
  const loading = ref(false)
  const error = ref('')
  const toast = reactive({ show: false, message: '', type: 'info' })

  let _toastTimer: ReturnType<typeof setTimeout> | null = null

  function showToast(message: string, type: string = 'info'): void {
    toast.message = message
    toast.type = type
    toast.show = true
    if (_toastTimer) clearTimeout(_toastTimer)
    _toastTimer = setTimeout(() => { toast.show = false }, 3000)
  }

  function _ensureConnected(): Promise<void> {
    return new Promise((resolve) => {
      if (pipelineSocket.connected) {
        resolve()
        return
      }
      const onConn = () => {
        pipelineSocket.off('connected', onConn)
        resolve()
      }
      pipelineSocket.on('connected', onConn)
    })
  }

  async function fetchAll(): Promise<void> {
    loading.value = true
    error.value = ''
    try {
      await _ensureConnected()
      await pipelineSocket.sendCommand('_system', 'sys_var.list', {})
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : '未知错误'
      error.value = '加载系统变量失败: ' + msg
      showToast(error.value, 'error')
    } finally {
      loading.value = false
    }
  }

  async function setVar(key: string, value: unknown): Promise<void> {
    error.value = ''
    try {
      await _ensureConnected()
      vars.value = { ...vars.value, [key]: value }
      await pipelineSocket.sendCommand('_system', 'sys_var.set', { key, value })
      showToast(`变量 "${key}" 已保存`, 'success')
    } catch (e: unknown) {
      const { [key]: _, ...rest } = vars.value
      vars.value = rest
      const msg = e instanceof Error ? e.message : '未知错误'
      error.value = '保存失败: ' + msg
      showToast(error.value, 'error')
    }
  }

  async function deleteVar(key: string): Promise<void> {
    error.value = ''
    try {
      await _ensureConnected()
      const { [key]: _, ...rest } = vars.value
      vars.value = rest
      await pipelineSocket.sendCommand('_system', 'sys_var.delete', { key })
      showToast(`变量 "${key}" 已删除`, 'success')
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : '未知错误'
      error.value = '删除失败: ' + msg
      showToast(error.value, 'error')
      fetchAll()
    }
  }

  function onListResult({ vars: data }: Record<string, unknown>): void {
    vars.value = (data as Record<string, unknown>) || {}
  }

  function onUpdated({ key, value }: Record<string, unknown>): void {
    vars.value = { ...vars.value, [key as string]: value }
  }

  function onDeleted({ key }: Record<string, unknown>): void {
    const { [key as string]: _, ...rest } = vars.value
    vars.value = rest
  }

  let _initialized = false
  function init(): void {
    if (_initialized) return
    _initialized = true
    pipelineSocket.on('sys_var.list_result', onListResult)
    pipelineSocket.on('sys_var.updated', onUpdated)
    pipelineSocket.on('sys_var.deleted', onDeleted)
    fetchAll()
  }

  return { vars, loading, error, toast, fetchAll, setVar, deleteVar, init }
})
