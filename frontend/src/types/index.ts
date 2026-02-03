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

export interface Source {
  document_id: number
  document_title: string
  section_title?: string
  article_number?: string
  page_number?: number
  relevance_score: number
  chunk_id?: string
  content?: string
}

export interface RetrievedChunk {
  chunk_id: string
  content: string
  score: number
  document_id: number
  document_title: string
  page_number?: number
  hierarchy_path?: string
}

export interface Message {
  id: number
  conversation_id: number
  role: 'user' | 'assistant' | 'system'
  content: string
  sources?: Source[]
  retrieved_chunks?: RetrievedChunk[]
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
  sources?: Source[]
}

// WebSocket Types
export type WSMessageType = 'metadata' | 'text' | 'done' | 'error' | 'pong' | 'chat' | 'ping'

export interface WSChatRequest {
  type: 'chat'
  message: string
  conversation_id?: number
  temperature?: number
  max_tokens?: number
}

export interface WSMetadataMessage {
  type: 'metadata'
  sources: Source[]
  retrieved_count: number
  retrieval_time: number
  conversation_id: number
}

export interface WSTextMessage {
  type: 'text'
  content: string
}

export interface WSDoneMessage {
  type: 'done'
  message_id: number
  generation_time: number
  total_time: number
  tokens_used: number
}

export interface WSErrorMessage {
  type: 'error'
  message: string
}

export type WSMessage = WSMetadataMessage | WSTextMessage | WSDoneMessage | WSErrorMessage

// Streaming State
export type StreamingState = 'idle' | 'connecting' | 'streaming' | 'done' | 'error'
export type ConnectionStatus = 'connected' | 'disconnected' | 'reconnecting'

// Chat Store State
export interface ChatState {
  // Conversations
  conversations: Conversation[]
  currentConversationId: number | null

  // Messages
  messages: Message[]
  streamingMessage: string
  streamingMetadata: WSMetadataMessage | null

  // State
  streamingState: StreamingState
  connectionStatus: ConnectionStatus
  error: string | null

  // Actions
  setConversations: (conversations: Conversation[]) => void
  setCurrentConversation: (id: number | null) => void
  addConversation: (conversation: Conversation) => void
  updateConversation: (id: number, updates: Partial<Conversation>) => void
  deleteConversation: (id: number) => void

  setMessages: (messages: Message[]) => void
  addMessage: (message: Message) => void
  appendToStreamingMessage: (text: string) => void
  setStreamingMetadata: (metadata: WSMetadataMessage | null) => void
  finalizeStreamingMessage: (message: Message) => void
  clearStreamingMessage: () => void

  setStreamingState: (state: StreamingState) => void
  setConnectionStatus: (status: ConnectionStatus) => void
  setError: (error: string | null) => void

  reset: () => void
}

// Conversation List Response
export interface ConversationListResponse {
  conversations: Conversation[]
  total: number
  skip: number
  limit: number
}

// Conversation Create/Update
export interface ConversationCreate {
  title: string
}

export interface ConversationUpdate {
  title?: string
  is_archived?: boolean
}

// Message Feedback
export interface MessageFeedback {
  rating: number // 1-5
  comment?: string
}
