/**
 * Pipeline WebSocket 客户端 —— 统一 /ws 端点
 *
 * 信封协议: {msg_id, flow_id, type, action, params, ts}
 * 支持 text frame (JSON) 和 binary frame (文件上传)
 *
 * 前端配置优先级：.env.development → import.meta.env.VITE_* → 硬编码默认值。
 * 每个常量都有对应的环境变量覆盖点（见下方 const 声明）。
 *
 * 🔗 跨服务对齐要求（此文件中的常量与后端必须一致）：
 *   - WS_URL → Python config.host + config.port
 *   - HEARTBEAT_INTERVAL → Python ws_main.HEARTBEAT_TIMEOUT 应 ≥ 此值 × 3
 *   - HEARTBEAT_TIMEOUT → Python ws_main.HEARTBEAT_TIMEOUT 应与此值一致
 */

import type { WsEnvelope } from '@/types/pipeline'

const WS_URL: string = import.meta.env.VITE_WS_URL || (
  // Auto-detect from current page: same host, backend port 8000
  location.hostname === 'localhost'
    ? 'ws://localhost:8000/ws'
    : `ws://${location.hostname}:8000/ws`
)
const RECONNECT_INITIAL: number = import.meta.env.VITE_WS_RECONNECT_INITIAL ? Number(import.meta.env.VITE_WS_RECONNECT_INITIAL) : 3000
const RECONNECT_MAX: number = import.meta.env.VITE_WS_RECONNECT_MAX ? Number(import.meta.env.VITE_WS_RECONNECT_MAX) : 30000
const CHUNK_SIZE: number = import.meta.env.VITE_UPLOAD_CHUNK_SIZE ? Number(import.meta.env.VITE_UPLOAD_CHUNK_SIZE) : 256 * 1024
const HEARTBEAT_INTERVAL: number = import.meta.env.VITE_WS_HEARTBEAT_INTERVAL ? Number(import.meta.env.VITE_WS_HEARTBEAT_INTERVAL) : 30000
const HEARTBEAT_TIMEOUT: number = import.meta.env.VITE_WS_HEARTBEAT_TIMEOUT ? Number(import.meta.env.VITE_WS_HEARTBEAT_TIMEOUT) : 90000
const WS_AUTH_TOKEN: string = import.meta.env.VITE_WS_AUTH_TOKEN || ''

// ── 类型定义 ──────────────────────────────────────────────────

type EventHandler = (params: Record<string, unknown>) => void

interface PendingAck {
  resolve: (value: Record<string, unknown>) => void
  reject: (reason: Error) => void
  timer: ReturnType<typeof setTimeout>
}

// ── PipelineSocket ────────────────────────────────────────────

class PipelineSocket {
  private url: string
  private ws: WebSocket | null = null
  private handlers: Map<string, EventHandler[]> = new Map()
  private _ackResolvers: Map<string, PendingAck> = new Map()
  private _reconnectAttempts: number = 0
  private _reconnectTimer: ReturnType<typeof setTimeout> | null = null
  private _intentionalClose: boolean = false
  private _connected: boolean = false
  private _heartbeatTimer: ReturnType<typeof setInterval> | null = null
  private _lastPong: number = Date.now()

  activeFlowId: string | null = null

  constructor() {
    this.url = WS_AUTH_TOKEN ? `${WS_URL}?token=${encodeURIComponent(WS_AUTH_TOKEN)}` : WS_URL
  }

  get connected(): boolean {
    return this._connected
  }

  // ── 连接管理 ──────────────────────────────────────────────

  connect(): void {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) return
    this._intentionalClose = false
    // 取消待执行的 reconnect timer，避免手动 connect 后 timer 再次触发创建重复连接
    if (this._reconnectTimer) {
      clearTimeout(this._reconnectTimer)
      this._reconnectTimer = null
    }

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
      this._lastPong = Date.now()
      this._startHeartbeat()
      this.emit('connected', {})
      // Re-subscribe to current flow after reconnect so broadcasts (node.created etc.) reach us
      if (this.activeFlowId) {
        try {
          this.sendCommand(this.activeFlowId, 'flow.load', {}).catch(() => {})
        } catch { /* ignore — editor will retry on user action */ }
      }
    }

    this.ws.onmessage = (event: MessageEvent) => {
      if (event.data instanceof ArrayBuffer) {
        // Binary frame (server→client is not used for now)
        return
      }
      if (event.data === 'pong') {
        this._lastPong = Date.now()
        return
      }
      try {
        const msg: WsEnvelope = JSON.parse(event.data as string)
        this._dispatch(msg)
      } catch (e) {
        console.error('[PipelineWS] Parse error:', e)
      }
    }

    this.ws.onclose = () => {
      console.log('[PipelineWS] Disconnected')
      this._connected = false
      this._ackResolvers.forEach(({ reject, timer }) => {
        clearTimeout(timer)
        reject(new Error('Connection lost'))
      })
      this._ackResolvers.clear()
      this.emit('disconnected', {})
      if (!this._intentionalClose) {
        this._scheduleReconnect()
      }
    }

    this.ws.onerror = (err: Event) => {
      console.error('[PipelineWS] Error:', err)
    }
  }

  disconnect(): void {
    this._intentionalClose = true
    this._connected = false
    this._stopHeartbeat()
    this.handlers.clear()
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

  private _startHeartbeat(): void {
    this._stopHeartbeat()
    this._heartbeatTimer = setInterval(() => {
      if (Date.now() - this._lastPong > HEARTBEAT_TIMEOUT) {
        console.warn('[PipelineWS] Heartbeat timeout, reconnecting')
        this._connected = false
        this._stopHeartbeat()
        if (this.ws) {
          this.ws.close()
          this.ws = null
        }
        this.emit('disconnected', {})
        this._scheduleReconnect()
        return
      }
      if (this.ws && this.ws.readyState === WebSocket.OPEN) {
        this.ws.send('ping')
      }
    }, HEARTBEAT_INTERVAL)
  }

  private _stopHeartbeat(): void {
    if (this._heartbeatTimer) {
      clearInterval(this._heartbeatTimer)
      this._heartbeatTimer = null
    }
  }

  private _scheduleReconnect(): void {
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
  sendCommand(flowId: string, action: string, params: Record<string, unknown> = {}, msgId?: string | null): Promise<Record<string, unknown>> {
    msgId = msgId || crypto.randomUUID()
    const msg: WsEnvelope = {
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
        this._ackResolvers.delete(msgId!)
        reject(new Error(`Command timeout: ${action}`))
      }, 15000)
      this._ackResolvers.set(msgId!, { resolve, reject, timer })
    })
  }

  /**
   * 发送二进制数据块（文件上传）
   */
  sendBinaryChunk(msgId: string, chunk: ArrayBuffer): void {
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
  async uploadFile(
    flowId: string,
    file: File,
    nodeId?: string | null,
    onReady?: ((uploadId: string) => void) | null,
  ): Promise<string> {
    const msgId = crypto.randomUUID()

    // ① 发起上传请求（使用同一 msgId，后续二进制帧共用）
    await this.sendCommand(flowId, 'file.upload_start', {
      name: file.name,
      size: file.size,
      mime_type: file.type,
      node_id: nodeId,
    }, msgId)

    // ② 等待 ready 事件
    const readyEvent = await this._waitForEvent('file.upload_ready', 10000)
    const uploadId = readyEvent.upload_id as string

    // 通知调用方 upload_id 已就绪（用于注册到 files store）
    onReady?.(uploadId)

    // ③ 分块发送（逐片读取，避免大文件全量加载到内存）
    let offset = 0
    while (offset < file.size) {
      const slice = file.slice(offset, offset + CHUNK_SIZE)
      const chunk = await slice.arrayBuffer()
      this.sendBinaryChunk(msgId, chunk)
      offset += CHUNK_SIZE
    }

    // ④ 等待完成
    const result = await this._waitForEvent('file.upload_done', 60000)
    return result.file_id as string
  }

  // ── 消息分发 ──────────────────────────────────────────────

  private _dispatch(msg: WsEnvelope): void {
    const { type, action, params, ref_msg_id } = msg

    switch (type) {
      case 'event':
        if (action === 'node.created') {
          console.log('[PipelineWS] ← node.created event received:', params)
        }
        this.emit(action, params)
        this.emit('message', msg as unknown as Record<string, unknown>)
        break
      case 'ack': {
        if (ref_msg_id) {
          const pending = this._ackResolvers.get(ref_msg_id)
          if (pending) {
            clearTimeout(pending.timer)
            this._ackResolvers.delete(ref_msg_id)
            pending.resolve((params as Record<string, unknown>) || { ok: true })
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
            pending.reject(new Error((params as Record<string, unknown>)?.message as string || 'Unknown error'))
          }
        }
        this.emit('error', msg as unknown as Record<string, unknown>)
        break
      }
      default:
        this.emit('message', msg as unknown as Record<string, unknown>)
    }
  }

  _waitForEvent(action: string, timeoutMs: number = 15000): Promise<Record<string, unknown>> {
    return new Promise((resolve, reject) => {
      const timer = setTimeout(() => {
        this.off(action, handler)
        reject(new Error(`Event timeout: ${action}`))
      }, timeoutMs)

      const handler: EventHandler = (params: Record<string, unknown>) => {
        clearTimeout(timer)
        this.off(action, handler)
        resolve(params)
      }
      this.on(action, handler)
    })
  }

  // ── 事件系统 ──────────────────────────────────────────────

  on(type: string, handler: EventHandler): void {
    if (!this.handlers.has(type)) this.handlers.set(type, [])
    const list = this.handlers.get(type)!
    if (!list.includes(handler)) list.push(handler)
  }

  off(type: string, handler: EventHandler): void {
    if (!this.handlers.has(type)) return
    const list = this.handlers.get(type)!
    const idx = list.indexOf(handler)
    if (idx > -1) list.splice(idx, 1)
  }

  emit(type: string, data: Record<string, unknown>): void {
    const list = this.handlers.get(type) || []
    list.forEach((fn) => {
      try { fn(data) } catch (e) { console.error(`[PipelineWS] Handler error (${type}):`, e) }
    })
  }
}

export const pipelineSocket = new PipelineSocket()
