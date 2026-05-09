/**
 * Notifications Store — 通知铃铛状态
 *
 * 处理 important_update 推送、notification.list_result 分页查询、
 * notification.unread 连接恢复、notification.mark_read 已读标记。
 */

import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { pipelineSocket } from '@/api/pipeline.js'

const MAX_ITEMS = 50

export const useNotificationsStore = defineStore('notifications', () => {
  const items = ref([])       // NotificationItem[]
  const unread = ref(0)
  const isOpen = ref(false)
  const hasMore = ref(false)   // 后端是否还有更多历史通知
  const _activeFlowId = ref(null)

  const hasUnread = computed(() => unread.value > 0)

  // ── 实时推送 ──────────────────────────────────────────────

  function onImportantUpdate(params) {
    const { notification_id, title, content, level, node_id, timestamp } = params
    const item = {
      id: notification_id || crypto.randomUUID(),
      title,
      content,
      level: level || 'info',
      node_id: node_id || null,
      timestamp: timestamp || new Date().toISOString(),
      read: false,
    }
    items.value.unshift(item)
    unread.value++

    // 裁剪
    if (items.value.length > MAX_ITEMS) {
      const removed = items.value.splice(MAX_ITEMS)
      const removedUnread = removed.filter((i) => !i.read).length
      unread.value = Math.max(0, unread.value - removedUnread)
    }
  }

  // ── 分页查询结果 ──────────────────────────────────────────

  function onListResult(params) {
    const { items: newItems, unread: serverUnread, has_more } = params
    // 替换或追加
    if (!_loadingMore.value) {
      items.value = newItems
    } else {
      items.value.push(...newItems)
    }
    unread.value = serverUnread
    hasMore.value = has_more
    _loadingMore.value = false
  }

  // ── 连接恢复时的未读计数 ──────────────────────────────────

  function onUnreadPush(params) {
    const { flow_id, unread: count } = params
    // 如果当前活跃 flow 匹配，更新未读数
    if (flow_id === _activeFlowId.value) {
      unread.value = count
    }
  }

  // ── 已读确认 ──────────────────────────────────────────────

  function onReadConfirm(params) {
    const { notification_id, unread: serverUnread } = params
    unread.value = serverUnread
    if (notification_id) {
      const item = items.value.find((i) => i.id === notification_id)
      if (item) item.read = true
    } else {
      // 全部已读
      items.value.forEach((i) => { i.read = true })
    }
  }

  // ── 前端操作 ──────────────────────────────────────────────

  const _loadingMore = ref(false)

  /**
   * 加载当前 flow 的历史通知
   */
  function fetchList(flowId) {
    _activeFlowId.value = flowId
    pipelineSocket.sendCommand(flowId, 'notification.list', { flow_id: flowId, limit: 20 })
  }

  /**
   * 加载更多（cursor 分页）
   */
  function loadMore() {
    if (!hasMore.value || _loadingMore.value || items.value.length === 0) return
    _loadingMore.value = true
    const lastId = items.value[items.value.length - 1].id
    pipelineSocket.sendCommand(_activeFlowId.value, 'notification.list', {
      flow_id: _activeFlowId.value,
      limit: 20,
      before: lastId,
    })
  }

  function markAllRead() {
    const flowId = _activeFlowId.value
    if (!flowId) return
    pipelineSocket.sendCommand(flowId, 'notification.mark_read', { flow_id: flowId })
  }

  function markRead(notificationId) {
    const flowId = _activeFlowId.value
    if (!flowId) return
    pipelineSocket.sendCommand(flowId, 'notification.mark_read', {
      flow_id: flowId,
      notification_id: notificationId,
    })
  }

  function toggle() {
    isOpen.value = !isOpen.value
  }

  function close() {
    isOpen.value = false
  }

  // ── 初始化 ────────────────────────────────────────────────

  let _initialized = false
  function init() {
    if (_initialized) return
    _initialized = true
    pipelineSocket.on('important_update', onImportantUpdate)
    pipelineSocket.on('notification.list_result', onListResult)
    pipelineSocket.on('notification.unread', onUnreadPush)
    pipelineSocket.on('notification.read', onReadConfirm)
  }

  return {
    items, unread, isOpen, hasUnread, hasMore, _activeFlowId,
    markAllRead, markRead, toggle, close, init,
    fetchList, loadMore,
  }
})
