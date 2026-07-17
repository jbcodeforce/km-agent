import { describe, it, expect } from 'vitest'
import { parseSaveCommand } from './agentOs.js'

describe('parseSaveCommand', () => {
  it('parses /save filename', () => {
    expect(parseSaveCommand('/save notes.md')).toBe('notes.md')
    expect(parseSaveCommand('/SAVE my-notes')).toBe('my-notes')
    expect(parseSaveCommand('  /save  foo.md  ')).toBe('foo.md')
  })

  it('returns null for non-save messages', () => {
    expect(parseSaveCommand('save notes.md')).toBe(null)
    expect(parseSaveCommand('/save')).toBe(null)
    expect(parseSaveCommand('/save a b')).toBe(null)
    expect(parseSaveCommand('What is Flink?')).toBe(null)
  })
})
