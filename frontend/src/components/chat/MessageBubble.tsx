import { User, Bot, Copy, Check } from 'lucide-react'
import { useState } from 'react'
import MarkdownIt from 'markdown-it'
import type { Message } from '@/types'
import { CitationCard } from './CitationCard'

const md = new MarkdownIt({
  html: false,
  linkify: true,
  typographer: true,
  breaks: true,
})

interface MessageBubbleProps {
  message: Message
  isStreaming?: boolean
}

export const MessageBubble = ({ message, isStreaming = false }: MessageBubbleProps) => {
  const [copied, setCopied] = useState(false)
  const isUser = message.role === 'user'

  const handleCopy = async () => {
    await navigator.clipboard.writeText(message.content)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  const formatTime = (timestamp: string) => {
    const date = new Date(timestamp)
    return date.toLocaleTimeString('vi-VN', {
      hour: '2-digit',
      minute: '2-digit',
    })
  }

  const renderContent = () => {
    if (isUser) {
      // User messages: plain text
      return (
        <p className="text-sm text-gray-900 dark:text-gray-100 whitespace-pre-wrap">
          {message.content}
        </p>
      )
    } else {
      // Assistant messages: markdown
      const html = md.render(message.content)
      return (
        <div
          className="prose prose-sm dark:prose-invert max-w-none"
          dangerouslySetInnerHTML={{ __html: html }}
        />
      )
    }
  }

  return (
    <div className={`flex gap-3 ${isUser ? 'flex-row-reverse' : 'flex-row'}`}>
      {/* Avatar */}
      <div
        className={`flex-shrink-0 w-8 h-8 rounded-full flex items-center justify-center ${
          isUser
            ? 'bg-primary-600 text-white'
            : 'bg-gray-200 dark:bg-gray-700 text-gray-700 dark:text-gray-300'
        }`}
      >
        {isUser ? <User className="h-4 w-4" /> : <Bot className="h-4 w-4" />}
      </div>

      {/* Message Content */}
      <div className={`flex-1 ${isUser ? 'flex justify-end' : ''}`}>
        <div
          className={`max-w-3xl ${
            isUser
              ? 'bg-primary-600 text-white rounded-2xl rounded-tr-none'
              : 'bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-2xl rounded-tl-none'
          } px-4 py-3 shadow-sm`}
        >
          {renderContent()}

          {/* Message metadata */}
          <div
            className={`flex items-center gap-2 mt-2 text-xs ${
              isUser ? 'text-primary-100' : 'text-gray-500 dark:text-gray-400'
            }`}
          >
            <span>{formatTime(message.created_at)}</span>
            {message.processing_time && !isUser && (
              <>
                <span>•</span>
                <span>{message.processing_time.toFixed(1)}s</span>
              </>
            )}
            {message.tokens_used && !isUser && (
              <>
                <span>•</span>
                <span>{message.tokens_used} tokens</span>
              </>
            )}
            {!isStreaming && (
              <button
                onClick={handleCopy}
                className={`ml-auto p-1 rounded hover:bg-opacity-20 ${
                  isUser ? 'hover:bg-white' : 'hover:bg-gray-300 dark:hover:bg-gray-600'
                }`}
                title="Sao chép"
              >
                {copied ? (
                  <Check className="h-3 w-3" />
                ) : (
                  <Copy className="h-3 w-3" />
                )}
              </button>
            )}
          </div>
        </div>

        {/* Citations for assistant messages */}
        {!isUser && message.sources && message.sources.length > 0 && (
          <div className="mt-3">
            <CitationCard sources={message.sources} />
          </div>
        )}
      </div>
    </div>
  )
}
