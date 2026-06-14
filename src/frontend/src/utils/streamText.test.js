import { describe, it, expect } from 'vitest'
import { consumeLeadingNewlines } from './streamText.js'

describe('consumeLeadingNewlines', () => {
  it('buffers newline-only chunks', () => {
    expect(consumeLeadingNewlines('', '\n')).toEqual({ buffer: '\n', emit: null })
    expect(consumeLeadingNewlines('\n', '\r\n')).toEqual({ buffer: '\n\r\n', emit: null })
  })

  it('emits from the first non-newline character', () => {
    expect(consumeLeadingNewlines('\n\n', 'Hello')).toEqual({ buffer: '', emit: 'Hello' })
    expect(consumeLeadingNewlines('', '\n\nHi')).toEqual({ buffer: '', emit: 'Hi' })
  })

  it('preserves internal newlines after stream start', () => {
    expect(consumeLeadingNewlines('', 'Line one\nLine two')).toEqual({
      buffer: '',
      emit: 'Line one\nLine two'
    })
  })
})
