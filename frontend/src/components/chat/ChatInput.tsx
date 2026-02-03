import { Send } from 'lucide-react'
import { useState, useRef, useEffect, KeyboardEvent } from 'react'

interface ChatInputProps {
  onSend: (message: string) => void
  disabled?: boolean
  placeholder?: string
}

export const ChatInput = ({
  onSend,
  disabled = false,
  placeholder = 'Nhập câu hỏi về luật môi trường...',
}: ChatInputProps) => {
  const [message, setMessage] = useState('')
  const textareaRef = useRef<HTMLTextAreaElement>(null)

  // Auto-resize textarea
  useEffect(() => {
    const textarea = textareaRef.current
    if (textarea) {
      textarea.style.height = 'auto'
      textarea.style.height = `${Math.min(textarea.scrollHeight, 200)}px`
    }
  }, [message])

  const handleSend = () => {
    const trimmedMessage = message.trim()
    if (trimmedMessage && !disabled) {
      onSend(trimmedMessage)
      setMessage('')

      // Reset textarea height
      if (textareaRef.current) {
        textareaRef.current.style.height = 'auto'
      }
    }
  }

  const handleKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    // Ctrl+Enter or Cmd+Enter to send
    if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') {
      e.preventDefault()
      handleSend()
    }
  }

  return (
    <div className="border-t border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 p-4">
      <div className="max-w-4xl mx-auto">
        <div className="flex gap-2 items-end">
          <div className="flex-1 relative">
            <textarea
              ref={textareaRef}
              value={message}
              onChange={(e) => setMessage(e.target.value)}
              onKeyDown={handleKeyDown}
              disabled={disabled}
              placeholder={placeholder}
              rows={1}
              className="input w-full resize-none min-h-[44px] max-h-[200px] pr-12"
              style={{ paddingTop: '12px', paddingBottom: '12px' }}
            />
            <div className="absolute bottom-2 right-2 text-xs text-gray-400">
              {message.length > 0 && `${message.length} ký tự`}
            </div>
          </div>

          <button
            onClick={handleSend}
            disabled={disabled || !message.trim()}
            className="btn btn-primary h-[44px] px-4 flex items-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            <Send className="h-4 w-4" />
            <span className="hidden sm:inline">Gửi</span>
          </button>
        </div>

        <p className="text-xs text-gray-500 dark:text-gray-400 mt-2">
          Nhấn <kbd className="px-1.5 py-0.5 bg-gray-100 dark:bg-gray-700 rounded border border-gray-300 dark:border-gray-600 text-xs">
            Ctrl+Enter
          </kbd> để gửi tin nhắn
        </p>
      </div>
    </div>
  )
}
