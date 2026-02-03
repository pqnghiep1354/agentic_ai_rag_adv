import axios from 'axios'

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'
const BASE_URL = `${API_URL}/api/v1/admin`

// Add auth token to requests
axios.interceptors.request.use((config) => {
  const token = localStorage.getItem('token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

export interface DashboardStats {
  overview: {
    total_users: number
    total_documents: number
    total_conversations: number
    total_messages: number
    total_storage_bytes: number
    avg_document_size_bytes: number
  }
  active_users: {
    last_24h: number
    last_7d: number
    last_30d: number
  }
  documents: {
    by_status: {
      pending: number
      processing: number
      completed: number
      failed: number
    }
  }
  query_metrics: {
    total_queries_7d: number
    avg_processing_time: number
    total_tokens_7d: number
    avg_retrieval_score: number
    avg_feedback_rating: number | null
  }
  recent_activity: Array<{
    id: number
    query: string
    user: string
    conversation: string
    processing_time: number | null
    tokens_used: number | null
    timestamp: string
  }>
}

export interface DocumentAnalytics {
  time_range_days: number
  upload_trends: Array<{
    date: string
    count: number
  }>
  processing_performance: {
    total_processed: number
    avg_processing_seconds: number
    total_chunks: number
    avg_chunks_per_document: number
  }
  file_type_distribution: Array<{
    file_type: string
    count: number
    total_size_bytes: number
  }>
  top_uploaders: Array<{
    username: string
    upload_count: number
    total_size_bytes: number
  }>
}

export interface QueryAnalytics {
  time_range_days: number
  query_volume: Array<{
    date: string
    count: number
  }>
  performance: {
    total_queries: number
    min_time: number
    max_time: number
    avg_time: number
    p50_time: number
    p95_time: number
    p99_time: number
  }
  token_usage: {
    total_tokens: number
    avg_tokens: number
    max_tokens: number
  }
  feedback: {
    distribution: Record<number, number>
    total_responses: number
  }
  top_users: Array<{
    username: string
    conversations: number
    messages: number
    avg_processing_time: number
  }>
}

export interface User {
  id: number
  username: string
  email: string
  full_name: string | null
  is_active: boolean
  is_superuser: boolean
  created_at: string
}

export interface UsersListResponse {
  users: User[]
  total: number
  skip: number
  limit: number
}

export interface QueryLog {
  message_id: number
  query: string
  user: string
  conversation_id: number
  conversation_title: string
  processing_time: number | null
  tokens_used: number | null
  retrieval_score: number | null
  feedback_rating: number | null
  timestamp: string
}

export interface QueryLogsResponse {
  logs: QueryLog[]
  total: number
  skip: number
  limit: number
}

export const adminService = {
  // Get dashboard statistics
  async getDashboardStats(): Promise<DashboardStats> {
    const response = await axios.get<DashboardStats>(`${BASE_URL}/dashboard`)
    return response.data
  },

  // Get document analytics
  async getDocumentAnalytics(days: number = 30): Promise<DocumentAnalytics> {
    const response = await axios.get<DocumentAnalytics>(`${BASE_URL}/analytics/documents`, {
      params: { days },
    })
    return response.data
  },

  // Get query analytics
  async getQueryAnalytics(days: number = 30): Promise<QueryAnalytics> {
    const response = await axios.get<QueryAnalytics>(`${BASE_URL}/analytics/queries`, {
      params: { days },
    })
    return response.data
  },

  // List users
  async listUsers(params?: {
    skip?: number
    limit?: number
    search?: string
  }): Promise<UsersListResponse> {
    const response = await axios.get<UsersListResponse>(`${BASE_URL}/users`, {
      params,
    })
    return response.data
  },

  // Get query logs
  async getQueryLogs(params?: {
    skip?: number
    limit?: number
    user_id?: number
    min_processing_time?: number
  }): Promise<QueryLogsResponse> {
    const response = await axios.get<QueryLogsResponse>(`${BASE_URL}/logs/queries`, {
      params,
    })
    return response.data
  },
}
