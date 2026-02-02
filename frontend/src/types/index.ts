// Type definitions for the application

export interface User {
  id: number
  email: string
  username: string
  full_name?: string
  is_active: boolean
  is_superuser: boolean
  created_at: string
  updated_at: string
}

export type DocumentStatus = 'pending' | 'processing' | 'completed' | 'failed'

export interface Document {
  id: number
  title: string
  filename: string
  file_path: string
  file_type: string
  file_size: number
  mime_type?: string
  page_count?: number
  status: DocumentStatus
  processing_error?: string
  processing_time?: number
  chunk_count?: number
  entity_count?: number
  issuing_authority?: string
  issue_date?: string
  document_number?: string
  owner_id: number
  created_at: string
  updated_at: string
  processed_at?: string
}

export interface DocumentListResponse {
  documents: Document[]
  total: number
  skip: number
  limit: number
}

export interface Message {
  id: number
  conversation_id: number
  role: 'user' | 'assistant' | 'system'
  content: string
  sources?: any
  retrieved_chunks?: any[]
  retrieval_score?: number
  processing_time?: number
  tokens_used?: number
  feedback_rating?: number
  feedback_comment?: string
  created_at: string
}

export interface Conversation {
  id: number
  title: string
  user_id: number
  is_archived: boolean
  message_count: number
  created_at: string
  updated_at: string
  last_message_at?: string
  messages?: Message[]
}

export interface ChatRequest {
  message: string
  conversation_id?: number
}

export interface ChatResponse {
  message: Message
  conversation_id: number
  sources?: any[]
}
