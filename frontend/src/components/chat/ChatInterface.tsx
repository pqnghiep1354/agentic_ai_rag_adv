import { Wifi, WifiOff, RefreshCw, AlertCircle } from 'lucide-react'
import { useChat } from '@/hooks/useChat'
import { useChatStore } from '@/stores/chatStore'
import { MessageList } from './MessageList'
import { ChatInput } from './ChatInput'
import { ConversationList } from './ConversationList'
import { ExportButton } from './ExportButton'

export const ChatInterface = () => {
  const {
    messages,
    streamingMessage,
    connectionStatus,
    error,
    isConnected,
    isStreaming,
    sendMessage,
  } = useChat()

  const { currentConversationId, conversations } = useChatStore()

  const currentConversation = conversations.find((c) => c.id === currentConversationId)

  // Connection status indicator
  const renderConnectionStatus = () => {
    if (connectionStatus === 'connected') {
      return (
        <div className="flex items-center gap-2 text-green-600 dark:text-green-400">
          <Wifi className="h-4 w-4" />
          <span className="text-xs">Đã kết nối</span>
        </div>
      )
    } else if (connectionStatus === 'reconnecting') {
      return (
        <div className="flex items-center gap-2 text-yellow-600 dark:text-yellow-400">
          <RefreshCw className="h-4 w-4 animate-spin" />
          <span className="text-xs">Đang kết nối lại...</span>
        </div>
      )
    } else {
      return (
        <div className="flex items-center gap-2 text-red-600 dark:text-red-400">
          <WifiOff className="h-4 w-4" />
          <span className="text-xs">Mất kết nối</span>
        </div>
      )
    }
  }

  // Error banner
  const renderError = () => {
    if (!error) return null

    return (
      <div className="bg-red-50 dark:bg-red-900/20 border-l-4 border-red-500 p-4">
        <div className="flex items-start gap-3">
          <AlertCircle className="h-5 w-5 text-red-600 dark:text-red-400 flex-shrink-0 mt-0.5" />
          <div className="flex-1">
            <h3 className="text-sm font-medium text-red-800 dark:text-red-200">
              Đã xảy ra lỗi
            </h3>
            <p className="text-sm text-red-700 dark:text-red-300 mt-1">{error}</p>
          </div>
        </div>
      </div>
    )
  }

  const handleSendMessage = (messageText: string) => {
    sendMessage(messageText, {
      conversationId: currentConversationId || undefined,
    })
  }

  return (
    <div className="flex h-full bg-gray-50 dark:bg-gray-900">
      {/* Conversation Sidebar */}
      <ConversationList />

      {/* Main Chat Area */}
      <div className="flex flex-col flex-1">
        {/* Header */}
        <div className="bg-white dark:bg-gray-800 border-b border-gray-200 dark:border-gray-700 px-6 py-4">
          <div className="max-w-4xl mx-auto flex items-center justify-between gap-4">
            <div className="flex-1 min-w-0">
              <h1 className="text-xl font-bold text-gray-900 dark:text-gray-100 truncate">
                {currentConversation?.title || 'Hỏi Đáp Luật Môi Trường'}
              </h1>
              <p className="text-sm text-gray-600 dark:text-gray-400 mt-1">
                Tìm kiếm thông tin từ các văn bản pháp luật Việt Nam
              </p>
            </div>
            <div className="flex items-center gap-3">
              <ExportButton
                conversationId={currentConversationId}
                conversationTitle={currentConversation?.title}
              />
              {renderConnectionStatus()}
            </div>
          </div>
        </div>

        {/* Error banner */}
        {renderError()}

        {/* Messages */}
        <MessageList
          messages={messages}
          streamingMessage={streamingMessage}
          isStreaming={isStreaming}
          className="flex-1"
        />

        {/* Input */}
        <ChatInput
          onSend={handleSendMessage}
          disabled={!isConnected || isStreaming}
          placeholder={
            !isConnected
              ? 'Đang kết nối...'
              : isStreaming
              ? 'Đang xử lý câu hỏi...'
              : 'Nhập câu hỏi về luật môi trường...'
          }
        />
      </div>
    </div>
  )
}
