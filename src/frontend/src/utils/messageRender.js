import { marked } from 'marked'

marked.setOptions({
  breaks: true,
  gfm: true
})

/**
 * Render assistant markdown to HTML for v-html bubbles.
 * @param {string} content
 * @returns {string}
 */
export function renderMarkdown(content) {
  return marked.parse(String(content || ''))
}
