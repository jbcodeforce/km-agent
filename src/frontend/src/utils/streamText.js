/**
 * Hold leading newline-only SSE chunks until the first visible character arrives.
 * @param {string} buffer - Text buffered so far at the start of a stream
 * @param {string} chunk - New chunk from the stream
 * @returns {{ buffer: string, emit: string | null }}
 */
export function consumeLeadingNewlines(buffer, chunk) {
  const combined = buffer + chunk
  const idx = combined.search(/[^\n\r]/)
  if (idx === -1) {
    return { buffer: combined, emit: null }
  }
  return { buffer: '', emit: combined.slice(idx) }
}
