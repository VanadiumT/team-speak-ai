/**
 * SysVars Store — 系统变量管理
 *
 * 管理全局系统变量的 CRUD，监听 WS 事件实时同步。
 */

import { defineStore } from 'pinia'
import { ref, reactive } from 'vue'
import { pipelineSocket } from '@/api/pipeline.js'

export const useSysVarsStore = defineStore('sysvars', () => {
  const vars = ref({})
  const loading = ref(false)
  const error = ref('')
  const toast = reactive({ show: false, message: '', type: 'info' })

  let _toastTimer = null

  function showToast(message, type = 'info') {
    toast.message = message
    toast.type = type
    toast.show = true
    if (_toastTimer) clearTimeout(_toastTimer)
    _toastTimer = setTimeout(() => { toast.show = false }, 3000)
  }

  function _ensureConnected() {
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

  async function fetchAll() {
    loading.value = true
    error.value = ''
    try {
      await _ensureConnected()
      await pipelineSocket.sendCommand('_system', 'sys_var.list', {})
    } catch (e) {
      error.value = '加载系统变量失败: ' + (e.message || '未知错误')
      showToast(error.value, 'error')
    } finally {
      loading.value = false
    }
  }

  async function setVar(key, value) {
    error.value = ''
    try {
      await _ensureConnected()
      vars.value = { ...vars.value, [key]: value }
      await pipelineSocket.sendCommand('_system', 'sys_var.set', { key, value })
      showToast(`变量 "${key}" 已保存`, 'success')
    } catch (e) {
      // revert optimistic update
      const { [key]: _, ...rest } = vars.value
      vars.value = rest
      error.value = '保存失败: ' + (e.message || '未知错误')
      showToast(error.value, 'error')
    }
  }

  async function deleteVar(key) {
    error.value = ''
    try {
      await _ensureConnected()
      const prev = vars.value[key]
      const { [key]: _, ...rest } = vars.value
      vars.value = rest
      await pipelineSocket.sendCommand('_system', 'sys_var.delete', { key })
      showToast(`变量 "${key}" 已删除`, 'success')
    } catch (e) {
      error.value = '删除失败: ' + (e.message || '未知错误')
      showToast(error.value, 'error')
      // re-fetch to restore correct state
      fetchAll()
    }
  }

  function onListResult({ vars: data }) {
    vars.value = data || {}
  }

  function onUpdated({ key, value }) {
    vars.value = { ...vars.value, [key]: value }
  }

  function onDeleted({ key }) {
    const { [key]: _, ...rest } = vars.value
    vars.value = rest
  }

  let _initialized = false
  function init() {
    if (_initialized) return
    _initialized = true
    pipelineSocket.on('sys_var.list_result', onListResult)
    pipelineSocket.on('sys_var.updated', onUpdated)
    pipelineSocket.on('sys_var.deleted', onDeleted)
    fetchAll()
  }

  return { vars, loading, error, toast, fetchAll, setVar, deleteVar, init }
})
