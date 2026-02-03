import axios from 'axios'
import type {
  Conversation,
  ConversationListResponse,
  ConversationCreate,
  ConversationUpdate,
  MessageFeedback,
  Message,
} from '@/types'

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'
const BASE_URL = `${API_URL}/api/v1/chat`

// Add auth token to requests
axios.interceptors.request.use((config) => {
  const token = localStorage.getItem('token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

export const chatService = {
  // Get all conversations
  async getConversations(params?: {
    skip?: number
    limit?: number
    includeArchived?: boolean
  }): Promise<ConversationListResponse> {
    const response = await axios.get<ConversationListResponse>(`${BASE_URL}/conversations`, {
      params: {
        skip: params?.skip || 0,
        limit: params?.limit || 50,
        include_archived: params?.includeArchived || false,
      },
    })
    return response.data
  },

  // Get a single conversation with messages
  async getConversation(id: number): Promise<Conversation> {
    const response = await axios.get<Conversation>(`${BASE_URL}/conversations/${id}`)
    return response.data
  },

  // Create a new conversation
  async createConversation(data: ConversationCreate): Promise<Conversation> {
    const response = await axios.post<Conversation>(`${BASE_URL}/conversations`, data)
    return response.data
  },

  // Update a conversation
  async updateConversation(id: number, data: ConversationUpdate): Promise<Conversation> {
    const response = await axios.patch<Conversation>(`${BASE_URL}/conversations/${id}`, data)
    return response.data
  },

  // Delete a conversation
  async deleteConversation(id: number): Promise<void> {
    await axios.delete(`${BASE_URL}/conversations/${id}`)
  },

  // Submit feedback for a message
  async submitFeedback(messageId: number, feedback: MessageFeedback): Promise<Message> {
    const response = await axios.post<Message>(`${BASE_URL}/messages/${messageId}/feedback`, feedback)
    return response.data
  },
}
