import { defineStore } from 'pinia'
import { wsClient } from '@/api/websocket'
import { useConversationStore } from './conversation'

export const useAppStore = defineStore('app', {
  state: () => ({
    connected: false,
    status: 'disconnected',
    teamspeakConnected: false,
  }),

  actions: {
    initWebSocket() {
      wsClient.on('connected', () => {
        this.connected = true
        this.status = 'connected'
        // Initialize conversation store listeners
        const conversationStore = useConversationStore()
        conversationStore.init()
      })

      wsClient.on('disconnected', () => {
        this.connected = false
        this.status = 'disconnected'
      })

      wsClient.on('status', (data) => {
        this.status = data.status
        if (data.teamspeak_connected !== undefined) {
          this.teamspeakConnected = data.teamspeak_connected
        }
      })

      wsClient.on('teamspeak_connected', () => {
        this.teamspeakConnected = true
      })

      wsClient.on('teamspeak_disconnected', () => {
        this.teamspeakConnected = false
      })

      // Handle stt_result events
      wsClient.on('stt_result', (data) => {
        // Conversation store will handle this via its own listener
        // But we can also update app-level state here if needed
        console.log('STT result received:', data)
      })

      wsClient.on('voice_received', (data) => {
        console.log('Voice received:', data)
      })

      wsClient.connect()
    },

    disconnect() {
      wsClient.disconnect()
    },
  },
})
