import { useEffect, useRef } from 'react'
import { MessageCircle } from 'lucide-react'
import type { Message } from '@/types'
import { MessageBubble } from './MessageBubble'
import { StreamingIndicator } from './StreamingIndicator'

interface MessageListProps {
  messages: Message[]
  streamingMessage?: string
  isStreaming?: boolean
  className?: string
}

export const MessageList = ({
  messages,
  streamingMessage = '',
  isStreaming = false,
  className = '',
}: MessageListProps) => {
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const containerRef = useRef<HTMLDivElement>(null)

  // Auto-scroll to bottom when new messages arrive
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, streamingMessage])

  // Empty state
  if (messages.length === 0 && !isStreaming) {
    return (
      <div className={`flex-1 flex items-center justify-center ${className}`}>
        <div className="text-center max-w-md px-4">
          <div className="w-16 h-16 bg-primary-100 dark:bg-primary-900 rounded-full flex items-center justify-center mx-auto mb-4">
            <MessageCircle className="h-8 w-8 text-primary-600 dark:text-primary-400" />
          </div>
          <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100 mb-2">
            Chào mừng đến với Trợ lý Luật Môi Trường
          </h3>
          <p className="text-sm text-gray-600 dark:text-gray-400">
            Hãy đặt câu hỏi về các quy định pháp luật môi trường Việt Nam.
            Tôi sẽ tìm kiếm và cung cấp thông tin từ các văn bản pháp luật có liên quan.
          </p>
          <div className="mt-6 text-xs text-gray-500 dark:text-gray-500 space-y-1">
            <p>Ví dụ câu hỏi:</p>
            <ul className="text-left inline-block">
              <li>• Quy định về xử lý chất thải nguy hại là gì?</li>
              <li>• Mức phạt vi phạm môi trường như thế nào?</li>
              <li>• Điều kiện cấp giấy phép môi trường?</li>
            </ul>
          </div>
        </div>
      </div>
    )
  }

  return (
    <div
      ref={containerRef}
      className={`flex-1 overflow-y-auto ${className}`}
    >
      <div className="max-w-4xl mx-auto px-4 py-6 space-y-6">
        {/* Render all messages */}
        {messages.map((message) => (
          <MessageBubble key={message.id} message={message} />
        ))}

        {/* Streaming message (if any) */}
        {isStreaming && streamingMessage && (
          <div className="flex gap-3">
            <div className="flex-shrink-0 w-8 h-8 rounded-full flex items-center justify-center bg-gray-200 dark:bg-gray-700">
              <MessageCircle className="h-4 w-4 text-gray-700 dark:text-gray-300" />
            </div>
            <div className="flex-1">
              <div className="max-w-3xl bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-2xl rounded-tl-none px-4 py-3 shadow-sm">
                <div
                  className="prose prose-sm dark:prose-invert max-w-none"
                  dangerouslySetInnerHTML={{
                    __html: streamingMessage.replace(/\n/g, '<br />'),
                  }}
                />
                <div className="mt-2">
                  <StreamingIndicator />
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Scroll anchor */}
        <div ref={messagesEndRef} />
      </div>
    </div>
  )
}
