import { useState, useRef, useEffect } from 'react'
import { Download, FileText, File, Loader2, ChevronDown } from 'lucide-react'
import { useMutation } from '@tanstack/react-query'
import { exportService } from '@/services/export'

interface ExportButtonProps {
  conversationId: number | null
  conversationTitle?: string
}

type ExportFormat = 'pdf' | 'excel'

export const ExportButton = ({ conversationId, conversationTitle }: ExportButtonProps) => {
  const [isOpen, setIsOpen] = useState(false)
  const dropdownRef = useRef<HTMLDivElement>(null)

  // Close dropdown when clicking outside
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setIsOpen(false)
      }
    }

    document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [])

  // Export mutation
  const exportMutation = useMutation({
    mutationFn: async ({ format }: { format: ExportFormat }) => {
      if (!conversationId) throw new Error('No conversation selected')

      const timestamp = new Date().toISOString().split('T')[0]
      const filename = `${conversationTitle || 'conversation'}_${timestamp}.${format === 'pdf' ? 'pdf' : 'xlsx'}`

      if (format === 'pdf') {
        const blob = await exportService.exportToPDF(conversationId)
        exportService.downloadFile(blob, filename)
      } else {
        const blob = await exportService.exportToExcel(conversationId)
        exportService.downloadFile(blob, filename)
      }
    },
    onSuccess: () => {
      setIsOpen(false)
    },
  })

  const handleExport = (format: ExportFormat) => {
    exportMutation.mutate({ format })
  }

  const disabled = !conversationId || exportMutation.isPending

  return (
    <div className="relative" ref={dropdownRef}>
      <button
        onClick={() => setIsOpen(!isOpen)}
        disabled={disabled}
        className="btn btn-secondary flex items-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed"
        title="Xuất cuộc hội thoại"
      >
        {exportMutation.isPending ? (
          <Loader2 className="h-4 w-4 animate-spin" />
        ) : (
          <Download className="h-4 w-4" />
        )}
        <span className="hidden sm:inline">Xuất</span>
        <ChevronDown className="h-3 w-3" />
      </button>

      {/* Dropdown menu */}
      {isOpen && (
        <div className="absolute right-0 mt-2 w-48 bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg shadow-lg z-10">
          <div className="py-1">
            <button
              onClick={() => handleExport('pdf')}
              disabled={exportMutation.isPending}
              className="w-full px-4 py-2 text-left text-sm text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700 flex items-center gap-3 disabled:opacity-50"
            >
              <FileText className="h-4 w-4 text-red-500" />
              <div>
                <div className="font-medium">Xuất PDF</div>
                <div className="text-xs text-gray-500 dark:text-gray-400">
                  Tệp Adobe PDF
                </div>
              </div>
            </button>

            <button
              onClick={() => handleExport('excel')}
              disabled={exportMutation.isPending}
              className="w-full px-4 py-2 text-left text-sm text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700 flex items-center gap-3 disabled:opacity-50"
            >
              <File className="h-4 w-4 text-green-500" />
              <div>
                <div className="font-medium">Xuất Excel</div>
                <div className="text-xs text-gray-500 dark:text-gray-400">
                  Bảng tính Excel
                </div>
              </div>
            </button>
          </div>
        </div>
      )}

      {/* Error message */}
      {exportMutation.isError && (
        <div className="absolute right-0 mt-2 w-64 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg p-3 shadow-lg z-10">
          <p className="text-sm text-red-800 dark:text-red-200">
            {exportMutation.error instanceof Error
              ? exportMutation.error.message
              : 'Không thể xuất cuộc hội thoại'}
          </p>
        </div>
      )}
    </div>
  )
}
