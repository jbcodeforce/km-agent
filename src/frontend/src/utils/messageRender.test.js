import { describe, it, expect } from 'vitest'
import { renderMarkdown } from './messageRender.js'

describe('renderMarkdown', () => {
  it('renders headings and bold', () => {
    const html = renderMarkdown('## Title\n\n**bold**')
    expect(html).toContain('<h2')
    expect(html).toContain('<strong>bold</strong>')
  })

  it('renders fenced code blocks', () => {
    const html = renderMarkdown('```js\nconst x = 1\n```')
    expect(html).toContain('<code')
    expect(html).toContain('const x = 1')
  })
})
