import type { WSChatRequest, WSMessage } from '@/types'

type MessageHandler = (message: WSMessage) => void
type ErrorHandler = (error: Event) => void
type CloseHandler = (event: CloseEvent) => void
type OpenHandler = () => void

interface WebSocketServiceConfig {
  url: string
  reconnectInterval?: number
  maxReconnectAttempts?: number
}

export class WebSocketService {
  private ws: WebSocket | null = null
  private url: string
  private reconnectInterval: number
  private maxReconnectAttempts: number
  private reconnectAttempts: number = 0
  private reconnectTimeout: ReturnType<typeof setTimeout> | null = null
  private messageHandlers: Set<MessageHandler> = new Set()
  private errorHandlers: Set<ErrorHandler> = new Set()
  private closeHandlers: Set<CloseHandler> = new Set()
  private openHandlers: Set<OpenHandler> = new Set()
  private messageQueue: WSChatRequest[] = []
  private isManualClose: boolean = false

  constructor(config: WebSocketServiceConfig) {
    this.url = config.url
    this.reconnectInterval = config.reconnectInterval || 3000
    this.maxReconnectAttempts = config.maxReconnectAttempts || 5
  }

  connect(token: string): void {
    if (this.ws?.readyState === WebSocket.OPEN) {
      return
    }

    this.isManualClose = false
    const wsUrl = `${this.url}?token=${token}`

    try {
      this.ws = new WebSocket(wsUrl)

      this.ws.onopen = () => {
        console.log('WebSocket connected')
        this.reconnectAttempts = 0
        this.openHandlers.forEach((handler) => handler())

        // Send queued messages
        while (this.messageQueue.length > 0) {
          const message = this.messageQueue.shift()
          if (message) {
            this.send(message)
          }
        }

        // Start heartbeat
        this.startHeartbeat()
      }

      this.ws.onmessage = (event) => {
        try {
          const message: WSMessage = JSON.parse(event.data)
          this.messageHandlers.forEach((handler) => handler(message))
        } catch (error) {
          console.error('Failed to parse WebSocket message:', error)
        }
      }

      this.ws.onerror = (error) => {
        console.error('WebSocket error:', error)
        this.errorHandlers.forEach((handler) => handler(error))
      }

      this.ws.onclose = (event) => {
        console.log('WebSocket closed:', event.code, event.reason)
        this.stopHeartbeat()
        this.closeHandlers.forEach((handler) => handler(event))

        // Attempt to reconnect if not a manual close
        if (!this.isManualClose && this.reconnectAttempts < this.maxReconnectAttempts) {
          this.reconnectAttempts++
          console.log(
            `Attempting to reconnect (${this.reconnectAttempts}/${this.maxReconnectAttempts})...`
          )
          this.reconnectTimeout = setTimeout(() => {
            this.connect(token)
          }, this.reconnectInterval)
        }
      }
    } catch (error) {
      console.error('Failed to create WebSocket connection:', error)
    }
  }

  disconnect(): void {
    this.isManualClose = true
    this.stopHeartbeat()

    if (this.reconnectTimeout) {
      clearTimeout(this.reconnectTimeout)
      this.reconnectTimeout = null
    }

    if (this.ws) {
      this.ws.close()
      this.ws = null
    }

    this.reconnectAttempts = 0
  }

  send(message: WSChatRequest): void {
    if (this.ws?.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify(message))
    } else {
      // Queue message for later if not connected
      this.messageQueue.push(message)
      console.warn('WebSocket not connected. Message queued.')
    }
  }

  onMessage(handler: MessageHandler): () => void {
    this.messageHandlers.add(handler)
    return () => this.messageHandlers.delete(handler)
  }

  onError(handler: ErrorHandler): () => void {
    this.errorHandlers.add(handler)
    return () => this.errorHandlers.delete(handler)
  }

  onClose(handler: CloseHandler): () => void {
    this.closeHandlers.add(handler)
    return () => this.closeHandlers.delete(handler)
  }

  onOpen(handler: OpenHandler): () => void {
    this.openHandlers.add(handler)
    return () => this.openHandlers.delete(handler)
  }

  isConnected(): boolean {
    return this.ws?.readyState === WebSocket.OPEN
  }

  getReadyState(): number | null {
    return this.ws?.readyState ?? null
  }

  // Heartbeat to keep connection alive
  private heartbeatInterval: ReturnType<typeof setInterval> | null = null

  private startHeartbeat(): void {
    this.heartbeatInterval = setInterval(() => {
      if (this.ws?.readyState === WebSocket.OPEN) {
        this.ws.send(JSON.stringify({ type: 'ping' }))
      }
    }, 30000) // Ping every 30 seconds
  }

  private stopHeartbeat(): void {
    if (this.heartbeatInterval) {
      clearInterval(this.heartbeatInterval)
      this.heartbeatInterval = null
    }
  }
}

// Singleton instance
let wsInstance: WebSocketService | null = null

export const getWebSocketService = (): WebSocketService => {
  if (!wsInstance) {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
    const host = window.location.host.includes('localhost')
      ? 'localhost:8000'
      : window.location.host

    wsInstance = new WebSocketService({
      url: `${protocol}//${host}/ws/chat`,
      reconnectInterval: 3000,
      maxReconnectAttempts: 5,
    })
  }

  return wsInstance
}
