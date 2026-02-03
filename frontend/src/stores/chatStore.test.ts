import { describe, it, expect, beforeEach } from 'vitest'
import { useChatStore } from './chatStore'

describe('chatStore', () => {
  beforeEach(() => {
    // Reset store before each test
    useChatStore.getState().reset()
  })

  describe('initial state', () => {
    it('has empty conversations', () => {
      const state = useChatStore.getState()
      expect(state.conversations).toEqual([])
    })

    it('has no current conversation', () => {
      const state = useChatStore.getState()
      expect(state.currentConversationId).toBeNull()
    })

    it('has empty messages', () => {
      const state = useChatStore.getState()
      expect(state.messages).toEqual([])
    })

    it('has idle streaming state', () => {
      const state = useChatStore.getState()
      expect(state.streamingState).toBe('idle')
    })

    it('has disconnected connection status', () => {
      const state = useChatStore.getState()
      expect(state.connectionStatus).toBe('disconnected')
    })
  })

  describe('conversation actions', () => {
    it('sets conversations', () => {
      const conversations = [
        { id: 1, title: 'Test 1', created_at: '2024-01-01' },
        { id: 2, title: 'Test 2', created_at: '2024-01-02' },
      ]

      useChatStore.getState().setConversations(conversations as any)

      expect(useChatStore.getState().conversations).toEqual(conversations)
    })

    it('sets current conversation and clears messages', () => {
      // First add some messages
      useChatStore.getState().addMessage({
        id: 1,
        role: 'user',
        content: 'Hello',
        conversation_id: 1,
        created_at: '',
      } as any)

      // Set current conversation
      useChatStore.getState().setCurrentConversation(2)

      const state = useChatStore.getState()
      expect(state.currentConversationId).toBe(2)
      expect(state.messages).toEqual([])
      expect(state.streamingMessage).toBe('')
    })

    it('adds conversation to beginning of list', () => {
      const existing = { id: 1, title: 'Existing', created_at: '2024-01-01' }
      const newConv = { id: 2, title: 'New', created_at: '2024-01-02' }

      useChatStore.getState().setConversations([existing] as any)
      useChatStore.getState().addConversation(newConv as any)

      const state = useChatStore.getState()
      expect(state.conversations[0].id).toBe(2)
      expect(state.conversations[1].id).toBe(1)
    })

    it('updates conversation', () => {
      const conv = { id: 1, title: 'Original', created_at: '2024-01-01' }
      useChatStore.getState().setConversations([conv] as any)

      useChatStore.getState().updateConversation(1, { title: 'Updated' })

      expect(useChatStore.getState().conversations[0].title).toBe('Updated')
    })

    it('deletes conversation', () => {
      const convs = [
        { id: 1, title: 'Test 1', created_at: '2024-01-01' },
        { id: 2, title: 'Test 2', created_at: '2024-01-02' },
      ]
      useChatStore.getState().setConversations(convs as any)

      useChatStore.getState().deleteConversation(1)

      expect(useChatStore.getState().conversations).toHaveLength(1)
      expect(useChatStore.getState().conversations[0].id).toBe(2)
    })

    it('clears messages when deleting current conversation', () => {
      useChatStore.getState().setConversations([{ id: 1, title: 'Test', created_at: '' }] as any)
      useChatStore.getState().setCurrentConversation(1)
      useChatStore.getState().addMessage({
        id: 1,
        role: 'user',
        content: 'Hello',
        conversation_id: 1,
        created_at: '',
      } as any)

      useChatStore.getState().deleteConversation(1)

      const state = useChatStore.getState()
      expect(state.currentConversationId).toBeNull()
      expect(state.messages).toEqual([])
    })
  })

  describe('message actions', () => {
    it('sets messages', () => {
      const messages = [
        { id: 1, role: 'user', content: 'Hello', conversation_id: 1, created_at: '' },
        { id: 2, role: 'assistant', content: 'Hi there', conversation_id: 1, created_at: '' },
      ]

      useChatStore.getState().setMessages(messages as any)

      expect(useChatStore.getState().messages).toEqual(messages)
    })

    it('adds message to end of list', () => {
      const msg1 = { id: 1, role: 'user', content: 'Hello', conversation_id: 1, created_at: '' }
      const msg2 = { id: 2, role: 'assistant', content: 'Hi', conversation_id: 1, created_at: '' }

      useChatStore.getState().addMessage(msg1 as any)
      useChatStore.getState().addMessage(msg2 as any)

      const state = useChatStore.getState()
      expect(state.messages).toHaveLength(2)
      expect(state.messages[0]).toEqual(msg1)
      expect(state.messages[1]).toEqual(msg2)
    })
  })

  describe('streaming actions', () => {
    it('appends to streaming message', () => {
      useChatStore.getState().appendToStreamingMessage('Hello')
      useChatStore.getState().appendToStreamingMessage(' World')

      expect(useChatStore.getState().streamingMessage).toBe('Hello World')
    })

    it('sets streaming metadata', () => {
      const metadata = { conversation_id: 1, retrieval_score: 0.85 }

      useChatStore.getState().setStreamingMetadata(metadata as any)

      expect(useChatStore.getState().streamingMetadata).toEqual(metadata)
    })

    it('finalizes streaming message', () => {
      useChatStore.getState().appendToStreamingMessage('Streaming content')
      useChatStore.getState().setStreamingState('streaming')

      const finalMessage = {
        id: 1,
        role: 'assistant',
        content: 'Streaming content',
        conversation_id: 1,
        created_at: '',
      }

      useChatStore.getState().finalizeStreamingMessage(finalMessage as any)

      const state = useChatStore.getState()
      expect(state.messages).toHaveLength(1)
      expect(state.messages[0]).toEqual(finalMessage)
      expect(state.streamingMessage).toBe('')
      expect(state.streamingMetadata).toBeNull()
      expect(state.streamingState).toBe('done')
    })

    it('clears streaming message', () => {
      useChatStore.getState().appendToStreamingMessage('Content')
      useChatStore.getState().setStreamingState('streaming')

      useChatStore.getState().clearStreamingMessage()

      const state = useChatStore.getState()
      expect(state.streamingMessage).toBe('')
      expect(state.streamingMetadata).toBeNull()
      expect(state.streamingState).toBe('idle')
    })
  })

  describe('state actions', () => {
    it('sets streaming state', () => {
      useChatStore.getState().setStreamingState('streaming')
      expect(useChatStore.getState().streamingState).toBe('streaming')
    })

    it('sets connection status', () => {
      useChatStore.getState().setConnectionStatus('connected')
      expect(useChatStore.getState().connectionStatus).toBe('connected')
    })

    it('sets error', () => {
      useChatStore.getState().setError('Test error')
      expect(useChatStore.getState().error).toBe('Test error')
    })

    it('resets to initial state', () => {
      // Modify state
      useChatStore.getState().setConversations([{ id: 1, title: 'Test', created_at: '' }] as any)
      useChatStore.getState().setCurrentConversation(1)
      useChatStore.getState().addMessage({
        id: 1,
        role: 'user',
        content: 'Hello',
        conversation_id: 1,
        created_at: '',
      } as any)
      useChatStore.getState().setConnectionStatus('connected')

      // Reset
      useChatStore.getState().reset()

      const state = useChatStore.getState()
      expect(state.conversations).toEqual([])
      expect(state.currentConversationId).toBeNull()
      expect(state.messages).toEqual([])
      expect(state.streamingState).toBe('idle')
      expect(state.connectionStatus).toBe('disconnected')
    })
  })
})
