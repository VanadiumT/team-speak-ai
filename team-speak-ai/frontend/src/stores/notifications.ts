/**
 * Notifications Store — 通知铃铛状态
 */

import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { pipelineSocket } from '@/api/pipeline'

const MAX_ITEMS = 50

interface NotificationDisplayItem {
  id: string
  title: string
  content: string
  level: string
  node_id: string | null
  timestamp: string
  read: boolean
}

export const useNotificationsStore = defineStore('notifications', () => {
  const items = ref<NotificationDisplayItem[]>([])
  const unread = ref(0)
  const isOpen = ref(false)
  const hasMore = ref(false)
  const _activeFlowId = ref<string | null>(null)

  const hasUnread = computed(() => unread.value > 0)

  function onImportantUpdate(params: Record<string, unknown>): void {
    const { notification_id, title, content, level, node_id, timestamp } = params
    const item: NotificationDisplayItem = {
      id: (notification_id as string) || crypto.randomUUID(),
      title: title as string,
      content: content as string,
      level: (level as string) || 'info',
      node_id: (node_id as string) || null,
      timestamp: (timestamp as string) || new Date().toISOString(),
      read: false,
    }
    items.value.unshift(item)
    unread.value++

    if (items.value.length > MAX_ITEMS) {
      const removed = items.value.splice(MAX_ITEMS)
      const removedUnread = removed.filter((i) => !i.read).length
      unread.value = Math.max(0, unread.value - removedUnread)
    }
  }

  function onListResult(params: Record<string, unknown>): void {
    const { items: newItems, unread: serverUnread, has_more } = params as {
      items: NotificationDisplayItem[]; unread: number; has_more: boolean
    }
    if (!_loadingMore.value) {
      items.value = newItems
    } else {
      items.value.push(...newItems)
    }
    unread.value = serverUnread
    hasMore.value = has_more
    _loadingMore.value = false
  }

  function onUnreadPush(params: Record<string, unknown>): void {
    const { flow_id, unread: count } = params as { flow_id: string; unread: number }
    if (flow_id === _activeFlowId.value) {
      unread.value = count
    }
  }

  function onReadConfirm(params: Record<string, unknown>): void {
    const { notification_id, unread: serverUnread } = params as { notification_id?: string; unread: number }
    unread.value = serverUnread
    if (notification_id) {
      const item = items.value.find((i) => i.id === notification_id)
      if (item) item.read = true
    } else {
      items.value.forEach((i) => { i.read = true })
    }
  }

  const _loadingMore = ref(false)

  function fetchList(flowId: string): void {
    _activeFlowId.value = flowId
    pipelineSocket.sendCommand(flowId, 'notification.list', { flow_id: flowId, limit: 20 })
  }

  function loadMore(): void {
    if (!hasMore.value || _loadingMore.value || items.value.length === 0) return
    _loadingMore.value = true
    const lastId = items.value[items.value.length - 1].id
    pipelineSocket.sendCommand(_activeFlowId.value!, 'notification.list', {
      flow_id: _activeFlowId.value,
      limit: 20,
      before: lastId,
    })
  }

  function markAllRead(): void {
    const flowId = _activeFlowId.value
    if (!flowId) return
    pipelineSocket.sendCommand(flowId, 'notification.mark_read', { flow_id: flowId })
  }

  function markRead(notificationId: string): void {
    const flowId = _activeFlowId.value
    if (!flowId) return
    pipelineSocket.sendCommand(flowId, 'notification.mark_read', {
      flow_id: flowId,
      notification_id: notificationId,
    })
  }

  function toggle(): void {
    isOpen.value = !isOpen.value
  }

  function close(): void {
    isOpen.value = false
  }

  let _initialized = false
  function init(): void {
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
