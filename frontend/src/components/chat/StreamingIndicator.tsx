import { Loader2 } from 'lucide-react'

interface StreamingIndicatorProps {
  text?: string
}

export const StreamingIndicator = ({ text = 'Đang trả lời' }: StreamingIndicatorProps) => {
  return (
    <div className="flex items-center gap-2 text-primary-600 dark:text-primary-400">
      <Loader2 className="h-4 w-4 animate-spin" />
      <span className="text-sm font-medium">{text}</span>
      <div className="flex gap-1">
        <span className="animate-bounce" style={{ animationDelay: '0ms' }}>
          .
        </span>
        <span className="animate-bounce" style={{ animationDelay: '150ms' }}>
          .
        </span>
        <span className="animate-bounce" style={{ animationDelay: '300ms' }}>
          .
        </span>
      </div>
    </div>
  )
}
