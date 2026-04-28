/**
 * Notifications Store — 通知铃铛状态
 *
 * 处理 important_update 推送和 notification.list_result。
 */

import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { pipelineSocket } from '@/api/pipeline.js'

const MAX_ITEMS = 50

export const useNotificationsStore = defineStore('notifications', () => {
  const items = ref([])       // NotificationItem[]
  const unread = ref(0)
  const isOpen = ref(false)

  const hasUnread = computed(() => unread.value > 0)

  function onImportantUpdate({ title, content, level, node_id }) {
    const item = {
      id: crypto.randomUUID(),
      title,
      content,
      level: level || 'info',
      node_id: node_id || null,
      timestamp: new Date().toISOString(),
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

  function markAllRead() {
    items.value.forEach((i) => { i.read = true })
    unread.value = 0
  }

  function markRead(notificationId) {
    const item = items.value.find((i) => i.id === notificationId)
    if (item && !item.read) {
      item.read = true
      unread.value = Math.max(0, unread.value - 1)
    }
  }

  function toggle() {
    isOpen.value = !isOpen.value
  }

  function close() {
    isOpen.value = false
  }

  function init() {
    pipelineSocket.on('important_update', onImportantUpdate)
  }

  return {
    items, unread, isOpen, hasUnread,
    markAllRead, markRead, toggle, close, init,
  }
})
