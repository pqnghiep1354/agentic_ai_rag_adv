import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { ChatInput } from './ChatInput'

describe('ChatInput', () => {
  const mockOnSend = vi.fn()

  beforeEach(() => {
    mockOnSend.mockClear()
  })

  it('renders textarea with default placeholder', () => {
    render(<ChatInput onSend={mockOnSend} />)

    const textarea = screen.getByPlaceholderText('Nhập câu hỏi về luật môi trường...')
    expect(textarea).toBeInTheDocument()
  })

  it('renders textarea with custom placeholder', () => {
    render(<ChatInput onSend={mockOnSend} placeholder="Custom placeholder" />)

    const textarea = screen.getByPlaceholderText('Custom placeholder')
    expect(textarea).toBeInTheDocument()
  })

  it('renders send button', () => {
    render(<ChatInput onSend={mockOnSend} />)

    const button = screen.getByRole('button')
    expect(button).toBeInTheDocument()
  })

  it('disables textarea when disabled prop is true', () => {
    render(<ChatInput onSend={mockOnSend} disabled={true} />)

    const textarea = screen.getByRole('textbox')
    expect(textarea).toBeDisabled()
  })

  it('disables send button when input is empty', () => {
    render(<ChatInput onSend={mockOnSend} />)

    const button = screen.getByRole('button')
    expect(button).toBeDisabled()
  })

  it('enables send button when input has text', async () => {
    const user = userEvent.setup()
    render(<ChatInput onSend={mockOnSend} />)

    const textarea = screen.getByRole('textbox')
    await user.type(textarea, 'Hello')

    const button = screen.getByRole('button')
    expect(button).not.toBeDisabled()
  })

  it('calls onSend with message when button is clicked', async () => {
    const user = userEvent.setup()
    render(<ChatInput onSend={mockOnSend} />)

    const textarea = screen.getByRole('textbox')
    await user.type(textarea, 'Test message')

    const button = screen.getByRole('button')
    await user.click(button)

    expect(mockOnSend).toHaveBeenCalledWith('Test message')
  })

  it('clears input after sending', async () => {
    const user = userEvent.setup()
    render(<ChatInput onSend={mockOnSend} />)

    const textarea = screen.getByRole('textbox')
    await user.type(textarea, 'Test message')
    await user.click(screen.getByRole('button'))

    expect(textarea).toHaveValue('')
  })

  it('trims whitespace from message before sending', async () => {
    const user = userEvent.setup()
    render(<ChatInput onSend={mockOnSend} />)

    const textarea = screen.getByRole('textbox')
    await user.type(textarea, '  Test message  ')
    await user.click(screen.getByRole('button'))

    expect(mockOnSend).toHaveBeenCalledWith('Test message')
  })

  it('does not send empty message after trim', async () => {
    const user = userEvent.setup()
    render(<ChatInput onSend={mockOnSend} />)

    const textarea = screen.getByRole('textbox')
    await user.type(textarea, '   ')

    const button = screen.getByRole('button')
    expect(button).toBeDisabled()
  })

  it('shows character count when typing', async () => {
    const user = userEvent.setup()
    render(<ChatInput onSend={mockOnSend} />)

    const textarea = screen.getByRole('textbox')
    await user.type(textarea, 'Hello')

    expect(screen.getByText('5 ký tự')).toBeInTheDocument()
  })

  it('sends message with Ctrl+Enter', async () => {
    const user = userEvent.setup()
    render(<ChatInput onSend={mockOnSend} />)

    const textarea = screen.getByRole('textbox')
    await user.type(textarea, 'Test message')
    await user.keyboard('{Control>}{Enter}{/Control}')

    expect(mockOnSend).toHaveBeenCalledWith('Test message')
  })
})
