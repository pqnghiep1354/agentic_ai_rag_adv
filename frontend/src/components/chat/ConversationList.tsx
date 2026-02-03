import { useState, useEffect } from 'react'
import { Plus, MessageSquare, Trash2, Archive } from 'lucide-react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { chatService } from '@/services/chat'
import { useChatStore } from '@/stores/chatStore'

export const ConversationList = () => {
  const queryClient = useQueryClient()
  const {
    conversations,
    currentConversationId,
    setConversations,
    setCurrentConversation,
    addConversation,
    deleteConversation: deleteConversationFromStore,
  } = useChatStore()

  const [showArchived, setShowArchived] = useState(false)

  // Fetch conversations
  const { data, isLoading } = useQuery({
    queryKey: ['conversations', showArchived],
    queryFn: () => chatService.getConversations({ includeArchived: showArchived }),
  })

  // Update store when data changes
  useEffect(() => {
    if (data?.conversations) {
      setConversations(data.conversations)
    }
  }, [data, setConversations])

  // Create conversation mutation
  const createMutation = useMutation({
    mutationFn: () =>
      chatService.createConversation({
        title: `Cuộc hội thoại mới - ${new Date().toLocaleString('vi-VN')}`,
      }),
    onSuccess: (newConversation) => {
      addConversation(newConversation)
      setCurrentConversation(newConversation.id)
      queryClient.invalidateQueries({ queryKey: ['conversations'] })
    },
  })

  // Delete conversation mutation
  const deleteMutation = useMutation({
    mutationFn: (id: number) => chatService.deleteConversation(id),
    onSuccess: (_, id) => {
      deleteConversationFromStore(id)
      queryClient.invalidateQueries({ queryKey: ['conversations'] })
    },
  })

  const handleSelectConversation = (id: number) => {
    setCurrentConversation(id)
  }

  const handleDeleteConversation = (e: React.MouseEvent, id: number) => {
    e.stopPropagation()
    if (confirm('Bạn có chắc chắn muốn xóa cuộc hội thoại này?')) {
      deleteMutation.mutate(id)
    }
  }

  const formatDate = (dateString: string) => {
    const date = new Date(dateString)
    const now = new Date()
    const diffInHours = (now.getTime() - date.getTime()) / (1000 * 60 * 60)

    if (diffInHours < 24) {
      return date.toLocaleTimeString('vi-VN', {
        hour: '2-digit',
        minute: '2-digit',
      })
    } else if (diffInHours < 7 * 24) {
      return date.toLocaleDateString('vi-VN', {
        weekday: 'short',
      })
    } else {
      return date.toLocaleDateString('vi-VN', {
        day: '2-digit',
        month: '2-digit',
      })
    }
  }

  return (
    <div className="w-80 border-r border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 flex flex-col h-full">
      {/* Header */}
      <div className="p-4 border-b border-gray-200 dark:border-gray-700">
        <button
          onClick={() => createMutation.mutate()}
          disabled={createMutation.isPending}
          className="btn btn-primary w-full flex items-center justify-center gap-2"
        >
          <Plus className="h-4 w-4" />
          Cuộc hội thoại mới
        </button>
      </div>

      {/* Filter */}
      <div className="px-4 py-2 border-b border-gray-200 dark:border-gray-700">
        <button
          onClick={() => setShowArchived(!showArchived)}
          className="text-xs text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-gray-100 flex items-center gap-1"
        >
          <Archive className="h-3 w-3" />
          {showArchived ? 'Ẩn đã lưu trữ' : 'Hiện đã lưu trữ'}
        </button>
      </div>

      {/* Conversation list */}
      <div className="flex-1 overflow-y-auto">
        {isLoading ? (
          <div className="p-4 text-center text-sm text-gray-500">Đang tải...</div>
        ) : conversations.length === 0 ? (
          <div className="p-4 text-center text-sm text-gray-500 dark:text-gray-400">
            Chưa có cuộc hội thoại nào
          </div>
        ) : (
          <div className="py-2">
            {conversations.map((conversation) => (
              <button
                key={conversation.id}
                onClick={() => handleSelectConversation(conversation.id)}
                className={`w-full px-4 py-3 text-left hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors border-l-4 ${
                  currentConversationId === conversation.id
                    ? 'border-primary-600 bg-primary-50 dark:bg-primary-900/20'
                    : 'border-transparent'
                }`}
              >
                <div className="flex items-start justify-between gap-2">
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-1">
                      <MessageSquare className="h-4 w-4 text-gray-400 flex-shrink-0" />
                      <h3 className="text-sm font-medium text-gray-900 dark:text-gray-100 truncate">
                        {conversation.title}
                      </h3>
                    </div>
                    <div className="flex items-center gap-2 text-xs text-gray-500 dark:text-gray-400">
                      <span>{conversation.message_count} tin nhắn</span>
                      <span>•</span>
                      <span>
                        {formatDate(conversation.last_message_at || conversation.updated_at)}
                      </span>
                    </div>
                  </div>
                  <button
                    onClick={(e) => handleDeleteConversation(e, conversation.id)}
                    className="p-1 hover:bg-red-100 dark:hover:bg-red-900/30 rounded transition-colors"
                    title="Xóa"
                  >
                    <Trash2 className="h-4 w-4 text-gray-400 hover:text-red-600" />
                  </button>
                </div>
              </button>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
