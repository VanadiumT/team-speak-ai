<template>
  <div class="notification-wrapper">
    <button class="bell-btn" @click="store.toggle()" title="通知">
      <span class="material-symbols-outlined">notifications</span>
      <span v-if="store.hasUnread" class="badge">{{ store.unread > 99 ? '99+' : store.unread }}</span>
    </button>

    <!-- Dropdown -->
    <div v-if="store.isOpen" class="dropdown">
      <div class="dropdown-header">
        <span class="dropdown-title">通知</span>
        <button v-if="store.hasUnread" class="mark-read-btn" @click="store.markAllRead()">全部已读</button>
      </div>
      <div class="dropdown-list">
        <div v-if="store.items.length === 0" class="empty">暂无通知</div>
        <div
          v-for="item in store.items.slice(0, 20)"
          :key="item.id"
          class="notification-item"
          :class="{ unread: !item.read }"
          @click="store.markRead(item.id)"
        >
          <div class="notif-level" :class="item.level"></div>
          <div class="notif-content">
            <div class="notif-title">{{ item.title }}</div>
            <div class="notif-text">{{ item.content }}</div>
          </div>
        </div>
      </div>
    </div>

    <!-- Backdrop -->
    <div v-if="store.isOpen" class="backdrop" @click="store.close()"></div>
  </div>
</template>

<script setup>
import { useNotificationsStore } from '@/stores/notifications.js'

const store = useNotificationsStore()
</script>

<style scoped>
.notification-wrapper { position: relative; }

.bell-btn {
  position: relative;
  color: #94a3b8;
  background: none;
  border: none;
  cursor: pointer;
  padding: 4px;
  transition: color 0.2s;
}

.bell-btn:hover { color: #60a5fa; }

.bell-btn .material-symbols-outlined { font-size: 20px; }

.badge {
  position: absolute;
  top: 0;
  right: 0;
  min-width: 16px;
  height: 16px;
  background: #ef4444;
  color: white;
  font-size: 9px;
  font-family: 'Space Grotesk', sans-serif;
  font-weight: 700;
  border-radius: 9999px;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 0 4px;
  transform: translate(25%, -25%);
}

/* Dropdown */
.dropdown {
  position: absolute;
  top: 100%;
  right: 0;
  margin-top: 8px;
  width: 360px;
  max-height: 480px;
  background: #0f172a;
  border: 1px solid rgba(65, 71, 84, 0.5);
  border-radius: 8px;
  box-shadow: 0 16px 48px rgba(0, 0, 0, 0.5);
  z-index: 60;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.dropdown-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 16px;
  border-bottom: 1px solid rgba(65, 71, 84, 0.3);
}

.dropdown-title {
  font-size: 14px;
  font-weight: 600;
  color: #e2e8f0;
}

.mark-read-btn {
  font-size: 11px;
  color: #adc7ff;
  background: none;
  border: none;
  cursor: pointer;
  font-family: 'Space Grotesk', sans-serif;
}

.mark-read-btn:hover { text-decoration: underline; }

.dropdown-list { flex: 1; overflow-y: auto; }

.empty {
  padding: 24px;
  text-align: center;
  color: #64748b;
  font-size: 13px;
}

.notification-item {
  display: flex;
  align-items: flex-start;
  gap: 10px;
  padding: 10px 16px;
  border-bottom: 1px solid rgba(65, 71, 84, 0.15);
  cursor: pointer;
  transition: background 0.15s;
}

.notification-item:hover { background: rgba(255, 255, 255, 0.03); }

.notification-item.unread { background: rgba(173, 199, 255, 0.05); }

.notif-level {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  margin-top: 5px;
  flex-shrink: 0;
}

.notif-level.info { background: #adc7ff; }
.notif-level.warning { background: #ef6719; }
.notif-level.error { background: #ffb4ab; }
.notif-level.success { background: #4edea3; }

.notif-content { flex: 1; min-width: 0; }

.notif-title {
  font-size: 12px;
  font-weight: 600;
  color: #e0e2ed;
  margin-bottom: 2px;
}

.notif-text {
  font-size: 11px;
  color: #94a3b8;
  line-height: 1.4;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

/* Backdrop */
.backdrop {
  position: fixed;
  inset: 0;
  z-index: 55;
}
</style>
