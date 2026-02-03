import { FileText, ChevronDown, ChevronUp } from 'lucide-react'
import { useState } from 'react'
import type { Source } from '@/types'

interface CitationCardProps {
  sources: Source[]
  className?: string
}

export const CitationCard = ({ sources, className = '' }: CitationCardProps) => {
  const [isExpanded, setIsExpanded] = useState(false)

  if (!sources || sources.length === 0) {
    return null
  }

  const displaySources = isExpanded ? sources : sources.slice(0, 3)
  const hasMore = sources.length > 3

  return (
    <div className={`card bg-gray-50 dark:bg-gray-800 ${className}`}>
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          <FileText className="h-4 w-4 text-primary-600" />
          <span className="text-sm font-semibold text-gray-700 dark:text-gray-300">
            Nguồn tham khảo ({sources.length})
          </span>
        </div>
        {hasMore && (
          <button
            onClick={() => setIsExpanded(!isExpanded)}
            className="text-xs text-primary-600 hover:text-primary-700 flex items-center gap-1"
          >
            {isExpanded ? (
              <>
                Thu gọn <ChevronUp className="h-3 w-3" />
              </>
            ) : (
              <>
                Xem thêm <ChevronDown className="h-3 w-3" />
              </>
            )}
          </button>
        )}
      </div>

      <div className="space-y-2">
        {displaySources.map((source, index) => (
          <div
            key={`${source.document_id}-${index}`}
            className="p-3 bg-white dark:bg-gray-700 rounded-lg border border-gray-200 dark:border-gray-600 hover:border-primary-300 dark:hover:border-primary-600 transition-colors"
          >
            <div className="flex items-start justify-between gap-2">
              <div className="flex-1 min-w-0">
                <h4 className="text-sm font-medium text-gray-900 dark:text-gray-100 truncate">
                  {source.document_title}
                </h4>
                <div className="flex flex-wrap gap-2 mt-1 text-xs text-gray-600 dark:text-gray-400">
                  {source.section_title && (
                    <span className="inline-flex items-center px-2 py-0.5 rounded bg-blue-100 dark:bg-blue-900 text-blue-800 dark:text-blue-200">
                      {source.section_title}
                    </span>
                  )}
                  {source.article_number && (
                    <span className="inline-flex items-center px-2 py-0.5 rounded bg-green-100 dark:bg-green-900 text-green-800 dark:text-green-200">
                      Điều {source.article_number}
                    </span>
                  )}
                  {source.page_number && (
                    <span className="inline-flex items-center px-2 py-0.5 rounded bg-purple-100 dark:bg-purple-900 text-purple-800 dark:text-purple-200">
                      Trang {source.page_number}
                    </span>
                  )}
                </div>
              </div>
              <div className="flex-shrink-0">
                <div className="inline-flex items-center px-2 py-1 rounded-full bg-primary-100 dark:bg-primary-900 text-primary-800 dark:text-primary-200 text-xs font-medium">
                  {(source.relevance_score * 100).toFixed(0)}%
                </div>
              </div>
            </div>
          </div>
        ))}
      </div>

      {!isExpanded && hasMore && (
        <p className="text-xs text-gray-500 dark:text-gray-400 mt-2 text-center">
          Và {sources.length - 3} nguồn khác...
        </p>
      )}
    </div>
  )
}
