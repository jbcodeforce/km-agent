import { describe, it, expect } from 'vitest'
import {
  formatTraceLine,
  formatProgressUpdate,
  applyProgressUpdate,
  MAX_PROGRESS_CHARS
} from './agentOs.js'

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

describe('formatProgressUpdate', () => {
  it('returns line mode for tools', () => {
    expect(
      formatProgressUpdate('TeamToolCallStarted', {
        tool: { tool_name: 'search' }
      })
    ).toEqual({ mode: 'line', text: 'tool → search' })
  })

  it('streams reasoning deltas in append mode', () => {
    expect(
      formatProgressUpdate('TeamReasoningContentDelta', {
        reasoning_content: 'look at '
      })
    ).toEqual({ mode: 'append', text: 'look at ' })
  })

  it('keeps longer reasoning steps than the activity one-liner', () => {
    const long = 'x'.repeat(500)
    const u = formatProgressUpdate('TeamReasoningStep', {
      reasoning_content: long
    })
    expect(u?.mode).toBe('line')
    expect(u?.text).toBe(`reason: ${long}`)
  })
})

describe('applyProgressUpdate', () => {
  it('appends deltas and starts new lines', () => {
    let t = applyProgressUpdate('', { mode: 'line', text: 'reasoning…' })
    t = applyProgressUpdate(t, { mode: 'append', text: 'hello' })
    t = applyProgressUpdate(t, { mode: 'append', text: ' world' })
    t = applyProgressUpdate(t, { mode: 'line', text: 'tool → x' })
    expect(t).toBe('reasoning…\nhello world\ntool → x')
  })

  it('trims from the start when over the cap', () => {
    const big = 'a'.repeat(MAX_PROGRESS_CHARS)
    const next = applyProgressUpdate(big, { mode: 'append', text: 'XYZ' })
    expect(next.length).toBe(MAX_PROGRESS_CHARS)
    expect(next.endsWith('XYZ')).toBe(true)
  })
})
