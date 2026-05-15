import { describe, it, expect } from 'vitest'
import { formatTraceLine } from './agentOs.js'

describe('formatTraceLine', () => {
  it('formats team tool start', () => {
    expect(
      formatTraceLine('TeamToolCallStarted', {
        tool: { tool_name: 'read_file' }
      })
    ).toBe('tool → read_file')
  })

  it('formats reasoning step', () => {
    expect(
      formatTraceLine('TeamReasoningStep', {
        reasoning_content: 'Check wiki index first.'
      })
    ).toBe('reason: Check wiki index first.')
  })

  it('returns null for unrelated events', () => {
    expect(formatTraceLine('TeamRunContent', { content: 'hello' })).toBe(null)
  })
})
