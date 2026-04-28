/**
 * Pipeline WebSocket 客户端 —— 统一 /ws 端点
 *
 * 信封协议: {msg_id, flow_id, type, action, params, ts}
 * 支持 text frame (JSON) 和 binary frame (文件上传)
 */

const WS_URL = 'ws://localhost:8000/ws'
const RECONNECT_INITIAL = 3000
const RECONNECT_MAX = 30000
const CHUNK_SIZE = 256 * 1024 // 256KB

class PipelineSocket {
  constructor() {
    this.url = WS_URL
    this.ws = null
    this.handlers = new Map()
    this._ackResolvers = new Map()     // msg_id → {resolve, reject, timer}
    this._reconnectAttempts = 0
    this._reconnectTimer = null
    this._intentionalClose = false
    this._connected = false
    this.activeFlowId = null
  }

  get connected() {
    return this._connected
  }

  // ── 连接管理 ──────────────────────────────────────────────

  connect() {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) return
    this._intentionalClose = false

    try {
      this.ws = new WebSocket(this.url)
    } catch (e) {
      console.error('[PipelineWS] Connection failed:', e)
      this._scheduleReconnect()
      return
    }

    this.ws.onopen = () => {
      console.log('[PipelineWS] Connected')
      this._connected = true
      this._reconnectAttempts = 0
      this.emit('connected')
    }

    this.ws.onmessage = (event) => {
      if (event.data instanceof ArrayBuffer) {
        // Binary frame (server→client is not used for now)
        return
      }
      try {
        const msg = JSON.parse(event.data)
        this._dispatch(msg)
      } catch (e) {
        console.error('[PipelineWS] Parse error:', e)
      }
    }

    this.ws.onclose = () => {
      console.log('[PipelineWS] Disconnected')
      this._connected = false
      this.emit('disconnected')
      if (!this._intentionalClose) {
        this._scheduleReconnect()
      }
    }

    this.ws.onerror = (err) => {
      console.error('[PipelineWS] Error:', err)
    }
  }

  disconnect() {
    this._intentionalClose = true
    this._connected = false
    if (this._reconnectTimer) {
      clearTimeout(this._reconnectTimer)
      this._reconnectTimer = null
    }
    if (this.ws) {
      this.ws.close()
      this.ws = null
    }
    this._ackResolvers.forEach(({ reject, timer }) => {
      clearTimeout(timer)
      reject(new Error('Disconnected'))
    })
    this._ackResolvers.clear()
  }

  _scheduleReconnect() {
    if (this._reconnectTimer) clearTimeout(this._reconnectTimer)
    const delay = Math.min(
      RECONNECT_INITIAL * Math.pow(2, this._reconnectAttempts),
      RECONNECT_MAX
    )
    this._reconnectAttempts++
    console.log(`[PipelineWS] Reconnecting in ${delay}ms (attempt ${this._reconnectAttempts})`)
    this._reconnectTimer = setTimeout(() => this.connect(), delay)
  }

  // ── 消息发送 ──────────────────────────────────────────────

  /**
   * 发送命令，返回 Promise<params> (对应 ack 后的事件 params)
   */
  sendCommand(flowId, action, params = {}) {
    const msgId = crypto.randomUUID()
    const msg = {
      msg_id: msgId,
      flow_id: flowId,
      type: 'command',
      action,
      params,
      ts: Date.now(),
    }

    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify(msg))
    } else {
      return Promise.reject(new Error('Not connected'))
    }

    return new Promise((resolve, reject) => {
      const timer = setTimeout(() => {
        this._ackResolvers.delete(msgId)
        reject(new Error(`Command timeout: ${action}`))
      }, 15000)
      this._ackResolvers.set(msgId, { resolve, reject, timer })
    })
  }

  /**
   * 发送二进制数据块（文件上传）
   */
  sendBinaryChunk(msgId, chunk) {
    if (!this.ws || this.ws.readyState !== WebSocket.OPEN) return
    const encoder = new TextEncoder()
    const idBytes = encoder.encode(msgId)
    const header = new ArrayBuffer(4)
    new DataView(header).setUint32(0, idBytes.length, false)
    const combined = new Uint8Array(4 + idBytes.length + chunk.byteLength)
    combined.set(new Uint8Array(header), 0)
    combined.set(idBytes, 4)
    combined.set(new Uint8Array(chunk), 4 + idBytes.length)
    this.ws.send(combined)
  }

  /**
   * 上传文件（完整流程）
   */
  async uploadFile(flowId, file, nodeId = null) {
    const msgId = crypto.randomUUID()

    // ① 发起上传请求
    await this.sendCommand(flowId, 'file.upload_start', {
      name: file.name,
      size: file.size,
      mime_type: file.type,
      node_id: nodeId,
    })

    // ② 等待 ready 事件
    const readyEvent = await this._waitForEvent('file.upload_ready', 10000)
    const uploadId = readyEvent.upload_id

    // ③ 分块发送
    const buffer = await file.arrayBuffer()
    let offset = 0
    while (offset < buffer.byteLength) {
      const chunk = buffer.slice(offset, offset + CHUNK_SIZE)
      this.sendBinaryChunk(msgId, chunk)
      offset += CHUNK_SIZE
    }

    // ④ 等待完成
    const result = await this._waitForEvent('file.upload_done', 60000)
    return result.file_id
  }

  // ── 消息分发 ──────────────────────────────────────────────

  _dispatch(msg) {
    const { type, action, params, ref_msg_id } = msg

    switch (type) {
      case 'event':
        this.emit(action, params)
        this.emit('message', msg)
        break
      case 'ack': {
        // 解析对应的 pending Promise
        if (ref_msg_id) {
          const pending = this._ackResolvers.get(ref_msg_id)
          if (pending) {
            clearTimeout(pending.timer)
            this._ackResolvers.delete(ref_msg_id)
            pending.resolve(params || { ok: true })
          }
        }
        break
      }
      case 'error': {
        if (ref_msg_id) {
          const pending = this._ackResolvers.get(ref_msg_id)
          if (pending) {
            clearTimeout(pending.timer)
            this._ackResolvers.delete(ref_msg_id)
            pending.reject(new Error(params?.message || 'Unknown error'))
          }
        }
        this.emit('error', msg)
        break
      }
      default:
        this.emit('message', msg)
    }
  }

  _waitForEvent(action, timeoutMs = 15000) {
    return new Promise((resolve, reject) => {
      const timer = setTimeout(() => {
        this.off(action, handler)
        reject(new Error(`Event timeout: ${action}`))
      }, timeoutMs)

      const handler = (params) => {
        clearTimeout(timer)
        this.off(action, handler)
        resolve(params)
      }
      this.on(action, handler)
    })
  }

  // ── 事件系统 ──────────────────────────────────────────────

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
    list.forEach((fn) => {
      try { fn(data) } catch (e) { console.error(`[PipelineWS] Handler error (${type}):`, e) }
    })
  }
}

export const pipelineSocket = new PipelineSocket()
