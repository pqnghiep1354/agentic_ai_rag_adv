import { create } from 'zustand'
import type {
  ChatState,
  Conversation,
  Message,
  StreamingState,
  ConnectionStatus,
  WSMetadataMessage,
} from '@/types'

const initialState = {
  conversations: [],
  currentConversationId: null,
  messages: [],
  streamingMessage: '',
  streamingMetadata: null,
  streamingState: 'idle' as StreamingState,
  connectionStatus: 'disconnected' as ConnectionStatus,
  error: null,
}

export const useChatStore = create<ChatState>((set) => ({
  ...initialState,

  // Conversation actions
  setConversations: (conversations) => set({ conversations }),

  setCurrentConversation: (id) => set({ currentConversationId: id, messages: [], streamingMessage: '', streamingMetadata: null }),

  addConversation: (conversation) =>
    set((state) => ({
      conversations: [conversation, ...state.conversations],
    })),

  updateConversation: (id, updates) =>
    set((state) => ({
      conversations: state.conversations.map((conv) =>
        conv.id === id ? { ...conv, ...updates } : conv
      ),
    })),

  deleteConversation: (id) =>
    set((state) => ({
      conversations: state.conversations.filter((conv) => conv.id !== id),
      currentConversationId: state.currentConversationId === id ? null : state.currentConversationId,
      messages: state.currentConversationId === id ? [] : state.messages,
    })),

  // Message actions
  setMessages: (messages) => set({ messages }),

  addMessage: (message) =>
    set((state) => ({
      messages: [...state.messages, message],
    })),

  appendToStreamingMessage: (text) =>
    set((state) => ({
      streamingMessage: state.streamingMessage + text,
    })),

  setStreamingMetadata: (metadata) => set({ streamingMetadata: metadata }),

  finalizeStreamingMessage: (message) =>
    set((state) => ({
      messages: [...state.messages, message],
      streamingMessage: '',
      streamingMetadata: null,
      streamingState: 'done',
    })),

  clearStreamingMessage: () =>
    set({
      streamingMessage: '',
      streamingMetadata: null,
      streamingState: 'idle',
    }),

  // State actions
  setStreamingState: (streamingState) => set({ streamingState }),

  setConnectionStatus: (connectionStatus) => set({ connectionStatus }),

  setError: (error) => set({ error }),

  reset: () => set(initialState),
}))
