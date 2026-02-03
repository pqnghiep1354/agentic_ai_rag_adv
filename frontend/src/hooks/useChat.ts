import { useEffect, useCallback, useRef } from 'react'
import { useChatStore } from '@/stores/chatStore'
import { getWebSocketService } from '@/services/websocket'
import type { WSMessage, WSChatRequest } from '@/types'

export const useChat = () => {
  const wsService = useRef(getWebSocketService())
  const {
    messages,
    streamingMessage,
    streamingMetadata,
    streamingState,
    connectionStatus,
    error,
    currentConversationId,
    addMessage,
    appendToStreamingMessage,
    setStreamingMetadata,
    finalizeStreamingMessage,
    clearStreamingMessage,
    setStreamingState,
    setConnectionStatus,
    setError,
  } = useChatStore()

  // Connect to WebSocket when component mounts
  useEffect(() => {
    const token = localStorage.getItem('token')
    if (!token) {
      setError('No authentication token found')
      return
    }

    if (!wsService.current.isConnected()) {
      wsService.current.connect(token)
    }

    // Handle WebSocket messages
    const unsubscribeMessage = wsService.current.onMessage((message: WSMessage) => {
      switch (message.type) {
        case 'metadata':
          setStreamingMetadata(message)
          setStreamingState('streaming')
          break

        case 'text':
          appendToStreamingMessage(message.content)
          setStreamingState('streaming')
          break

        case 'done':
          // Finalize the assistant message
          const assistantMessage = {
            id: message.message_id,
            conversation_id: streamingMetadata?.conversation_id || currentConversationId || 0,
            role: 'assistant' as const,
            content: streamingMessage,
            sources: streamingMetadata?.sources || [],
            processing_time: message.total_time,
            tokens_used: message.tokens_used,
            created_at: new Date().toISOString(),
          }
          finalizeStreamingMessage(assistantMessage)
          break

        case 'error':
          setError(message.message)
          setStreamingState('error')
          clearStreamingMessage()
          break

        default:
          break
      }
    })

    // Handle WebSocket open
    const unsubscribeOpen = wsService.current.onOpen(() => {
      setConnectionStatus('connected')
      setError(null)
    })

    // Handle WebSocket close
    const unsubscribeClose = wsService.current.onClose((event) => {
      if (event.code === 1000) {
        // Normal closure
        setConnectionStatus('disconnected')
      } else {
        // Abnormal closure - attempting reconnection
        setConnectionStatus('reconnecting')
      }
    })

    // Handle WebSocket error
    const unsubscribeError = wsService.current.onError(() => {
      setConnectionStatus('disconnected')
      setError('WebSocket connection error')
    })

    // Cleanup on unmount
    return () => {
      unsubscribeMessage()
      unsubscribeOpen()
      unsubscribeClose()
      unsubscribeError()
    }
  }, [
    setStreamingMetadata,
    appendToStreamingMessage,
    finalizeStreamingMessage,
    clearStreamingMessage,
    setStreamingState,
    setConnectionStatus,
    setError,
    streamingMessage,
    streamingMetadata,
    currentConversationId,
  ])

  // Send a chat message
  const sendMessage = useCallback(
    (
      messageText: string,
      options?: {
        conversationId?: number
        temperature?: number
        maxTokens?: number
      }
    ) => {
      if (!messageText.trim()) {
        return
      }

      // Clear any previous error
      setError(null)

      // Add user message to store
      const userMessage = {
        id: Date.now(), // Temporary ID
        conversation_id: options?.conversationId || currentConversationId || 0,
        role: 'user' as const,
        content: messageText,
        created_at: new Date().toISOString(),
      }
      addMessage(userMessage)

      // Clear previous streaming state
      clearStreamingMessage()
      setStreamingState('connecting')

      // Send via WebSocket
      const wsMessage: WSChatRequest = {
        type: 'chat',
        message: messageText,
        conversation_id: options?.conversationId || currentConversationId || undefined,
        temperature: options?.temperature,
        max_tokens: options?.maxTokens,
      }

      wsService.current.send(wsMessage)
    },
    [
      currentConversationId,
      addMessage,
      clearStreamingMessage,
      setStreamingState,
      setError,
    ]
  )

  // Disconnect WebSocket
  const disconnect = useCallback(() => {
    wsService.current.disconnect()
    setConnectionStatus('disconnected')
  }, [setConnectionStatus])

  return {
    // State
    messages,
    streamingMessage,
    streamingMetadata,
    streamingState,
    connectionStatus,
    error,
    isConnected: connectionStatus === 'connected',
    isStreaming: streamingState === 'streaming',

    // Actions
    sendMessage,
    disconnect,
  }
}
