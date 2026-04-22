import { defineStore } from 'pinia'
import { wsClient } from '@/api/websocket'

export const useConversationStore = defineStore('conversation', {
  state: () => ({
    items: [],  // Array of conversation items
  }),

  actions: {
    init() {
      // Listen for voice received events
      wsClient.on('voice_received', (data) => {
        this.items.unshift({
          id: data.request_id,
          speaker: { id: data.sender_id, name: data.sender_name || 'Unknown' },
          stt: { text: '', status: 'pending' },
          timestamp: data.timestamp,
        })
        // Keep only last 50 items
        if (this.items.length > 50) {
          this.items.pop()
        }
      })

      // Listen for STT results
      wsClient.on('stt_result', (data) => {
        const item = this.items.find(i => i.id === data.request_id)
        if (item) {
          item.stt = { text: data.text, confidence: data.confidence }
        } else {
          // If no matching voice_received item, create new one
          this.items.unshift({
            id: data.request_id,
            speaker: { id: data.sender_id, name: data.sender_name || 'Unknown' },
            stt: { text: data.text, confidence: data.confidence },
            timestamp: data.timestamp,
          })
        }
      })
    },

    clear() {
      this.items = []
    },
  },
})