/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_WS_URL?: string
  readonly VITE_WS_RECONNECT_INITIAL?: string
  readonly VITE_WS_RECONNECT_MAX?: string
  readonly VITE_UPLOAD_CHUNK_SIZE?: string
  readonly VITE_WS_HEARTBEAT_INTERVAL?: string
  readonly VITE_WS_HEARTBEAT_TIMEOUT?: string
}

interface ImportMeta {
  readonly env: ImportMetaEnv
}
