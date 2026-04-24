/**
 * Pipeline WebSocket 客户端
 * 取代旧的 websocket.js，基于事件驱动
 */
class PipelineSocket {
  constructor() {
    this.url = 'ws://localhost:8000/ws/pipeline'
    this.ws = null
    this.handlers = new Map()
    this.reconnectInterval = 3000
    this.reconnectTimer = null
    this.intentionalClose = false
  }

  connect() {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) return
    this.intentionalClose = false
    this.ws = new WebSocket(this.url)

    this.ws.onopen = () => {
      console.log('[PipelineWS] Connected')
      this.emit('connected')
    }

    this.ws.onmessage = (event) => {
      try {
        const msg = JSON.parse(event.data)
        const { type, data } = msg
        this.emit(type, data)
        // 也触发通用 'message' 事件
        this.emit('message', msg)
      } catch (e) {
        console.error('[PipelineWS] Parse error:', e)
      }
    }

    this.ws.onclose = () => {
      console.log('[PipelineWS] Disconnected')
      this.emit('disconnected')
      if (!this.intentionalClose) {
        this.scheduleReconnect()
      }
    }

    this.ws.onerror = (err) => {
      console.error('[PipelineWS] Error:', err)
    }
  }

  scheduleReconnect() {
    if (this.reconnectTimer) clearTimeout(this.reconnectTimer)
    this.reconnectTimer = setTimeout(() => this.connect(), this.reconnectInterval)
  }

  disconnect() {
    this.intentionalClose = true
    if (this.reconnectTimer) {
      clearTimeout(this.reconnectTimer)
      this.reconnectTimer = null
    }
    if (this.ws) {
      this.ws.close()
      this.ws = null
    }
  }

  send(type, data = {}) {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify({ type, data }))
    }
  }

  on(type, handler) {
    if (!this.handlers.has(type)) this.handlers.set(type, [])
    this.handlers.get(type).push(handler)
  }

  off(type, handler) {
    if (!this.handlers.has(type)) return
    const list = this.handlers.get(type)
    const idx = list.indexOf(handler)
    if (idx > -1) list.splice(idx, 1)
  }

  emit(type, data) {
    const list = this.handlers.get(type) || []
    list.forEach((fn) => fn(data))
  }
}

export const pipelineSocket = new PipelineSocket()
