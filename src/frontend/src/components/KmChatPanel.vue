<template>
  <div class="chat-panel">
    <div class="chat-messages" ref="messagesContainer">
      <div v-if="messages.length === 0" class="chat-welcome">
        <div class="welcome-icon">
          <svg xmlns="http://www.w3.org/2000/svg" width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">
            <path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20"/>
            <path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z"/>
            <circle cx="10" cy="8" r="2"/>
            <path d="m20 13-1.5-1.5"/>
            <path d="M15 11.5 12 8"/>
          </svg>
        </div>
        <h3>Flink Studies expert</h3>
        <p>
          Ask about Apache Flink, streaming concepts, and this repository. The agent searches the indexed knowledge base first.
        </p>
        <div class="suggested-prompts">
          <button type="button" @click="sendSuggested('What are the core concepts of Flink?')">
            Core concepts
          </button>
          <button type="button" @click="sendSuggested('How does checkpointing work in Flink?')">
            Checkpointing
          </button>
          <button type="button" @click="sendSuggested('Where is the agentic Flink demo described in this repo?')">
            Repo demos
          </button>
        </div>
      </div>

      <template v-for="(msg, index) in messages" :key="index">
        <div :class="['message', msg.role]">
          <div class="message-avatar">
            <template v-if="msg.role === 'user'">
              <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/>
                <circle cx="12" cy="7" r="4"/>
              </svg>
            </template>
            <template v-else>
              <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20"/>
                <path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z"/>
              </svg>
            </template>
          </div>
          <div class="message-content">
            <template v-if="msg.role === 'assistant'">
              <div v-if="msg.streamComplete" class="message-toolbar">
                <div class="view-toggle" role="group" aria-label="Message view">
                  <button
                    type="button"
                    :class="{ active: getViewMode(index) === 'text' }"
                    @click="setViewMode(index, 'text')"
                  >
                    Text
                  </button>
                  <button
                    type="button"
                    :class="{ active: getViewMode(index) === 'markdown' }"
                    @click="setViewMode(index, 'markdown')"
                  >
                    Markdown
                  </button>
                </div>
                <button
                  type="button"
                  class="copy-btn"
                  :disabled="!msg.content"
                  @click="copyMessage(index)"
                >
                  {{ copiedIndex === index ? 'Copied' : 'Copy' }}
                </button>
              </div>
              <pre
                v-if="!msg.streamComplete || getViewMode(index) === 'text'"
                class="message-text plain"
              >{{ msg.content }}</pre>
              <div
                v-else
                class="message-text markdown"
                v-html="renderMarkdown(msg.content)"
              ></div>
              <div v-if="msg.streamComplete" class="stream-end">END</div>
            </template>
            <div v-else class="message-text user-text">{{ msg.content }}</div>
          </div>
        </div>
      </template>

      <div v-if="isLoading && (messages.length === 0 || messages[messages.length - 1]?.role !== 'assistant')" class="message assistant loading">
        <div class="message-avatar">
          <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20"/>
            <path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z"/>
          </svg>
        </div>
        <div class="message-content">
          <div class="typing-indicator">
            <span></span>
            <span></span>
            <span></span>
          </div>
        </div>
      </div>

      <div v-if="error" class="chat-error">
        <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <circle cx="12" cy="12" r="10"/>
          <line x1="12" y1="8" x2="12" y2="12"/>
          <line x1="12" y1="16" x2="12.01" y2="16"/>
        </svg>
        <span>{{ error }}</span>
        <button type="button" @click="error = null">Dismiss</button>
      </div>
    </div>

    <details v-if="traceLines.length" class="chat-trace">
      <summary>Activity <span class="trace-count">({{ traceLines.length }})</span></summary>
      <pre class="chat-trace-pre">{{ traceLines.join('\n') }}</pre>
    </details>

    <div class="chat-input-area">
      <div class="input-row">
        <textarea
          ref="inputField"
          v-model="inputMessage"
          @keydown.enter.exact.prevent="sendMessage"
          placeholder="Ask about Flink or this repository…"
          rows="1"
          :disabled="isLoading"
        ></textarea>
        <button
          type="button"
          class="send-btn"
          @click="sendMessage"
          :disabled="!inputMessage.trim() || isLoading"
        >
          <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <line x1="22" y1="2" x2="11" y2="13"/>
            <polygon points="22 2 15 22 11 13 2 9 22 2"/>
          </svg>
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
/**
 * Chat UI: message list, streaming assistant replies, optional Agno activity trace.
 * Hydrates from session chat_history when route.session_id is set.
 */
import { ref, watch, nextTick, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import {
  createTeamRunStream,
  getSession,
  chatHistoryToMessages
} from '@/services/agentOs.js'
import { consumeLeadingNewlines } from '@/utils/streamText.js'
import { renderMarkdown } from '@/utils/messageRender.js'

const props = defineProps({
  teamId: { type: String, required: true },
  userId: { type: String, required: true }
})

const emit = defineEmits(['run-complete'])

const route = useRoute()
const router = useRouter()

const messages = ref([])
const traceLines = ref([])
const MAX_TRACE_LINES = 200
const inputMessage = ref('')
const isLoading = ref(false)
const error = ref(null)
const messagesContainer = ref(null)
const inputField = ref(null)
/** @type {import('vue').Ref<Record<number, 'text' | 'markdown'>>} */
const messageViewModes = ref({})
/** @param {number} index */
function getViewMode(index) {
  const msg = messages.value[index]
  if (msg?.role === 'assistant' && !msg.streamComplete) return 'text'
  return messageViewModes.value[index] ?? 'markdown'
}

/** @param {number} index @param {'text' | 'markdown'} mode */
function setViewMode(index, mode) {
  messageViewModes.value = { ...messageViewModes.value, [index]: mode }
}

/** Scroll the message container after DOM updates. */
function scrollToBottom() {
  nextTick(() => {
    if (messagesContainer.value) {
      messagesContainer.value.scrollTop = messagesContainer.value.scrollHeight
    }
  })
}

/** Merge keys into the current route query (e.g. new session_id after first run). */
function mergeQuery(updates) {
  router.replace({
    query: {
      ...route.query,
      ...updates
    }
  })
}

/**
 * Load prior messages from AgentOS session chat_history.
 * @param {string | null | undefined} sessionId
 */
async function hydrateFromSession(sessionId) {
  if (!sessionId) {
    messages.value = []
    messageViewModes.value = {}
    return
  }
  error.value = null
  try {
    const s = await getSession(sessionId, { userId: props.userId })
    messages.value = chatHistoryToMessages(s.chat_history || [])
    messageViewModes.value = {}
    scrollToBottom()
  } catch (e) {
    error.value = e.message || 'Failed to load session'
    messages.value = []
    messageViewModes.value = {}
  }
}

watch(
  () => route.query.session_id,
  (sid) => {
    if (isLoading.value) return
    hydrateFromSession(sid || null)
  },
  { immediate: true }
)

watch(
  () => props.userId,
  () => {
    const sid = route.query.session_id
    if (sid) hydrateFromSession(sid)
  }
)

onMounted(() => {
  inputField.value?.focus()
})

/** POST a streaming agent run; append assistant chunks and emit run-complete on done. */
async function sendMessage() {
  const message = inputMessage.value.trim()
  if (!message || isLoading.value || !props.teamId) return

  messages.value.push({ role: 'user', content: message })
  inputMessage.value = ''
  scrollToBottom()

  isLoading.value = true
  error.value = null
  traceLines.value = []

  const sid = route.query.session_id || null
  let streamLeadBuffer = ''
  let streamTextStarted = false

  await createTeamRunStream(
    props.teamId,
    {
      message,
      sessionId: sid || undefined,
      userId: props.userId || undefined
    },
    {
      onSessionId: (id) => {
        if (id && id !== route.query.session_id) {
          mergeQuery({ session_id: id, user_id: props.userId })
        }
      },
      onTextChunk: (text) => {
        let toAppend = text
        if (!streamTextStarted) {
          const { buffer, emit } = consumeLeadingNewlines(streamLeadBuffer, text)
          streamLeadBuffer = buffer
          if (emit == null) return
          toAppend = emit
          streamTextStarted = true
        }

        const last = messages.value[messages.value.length - 1]
        if (last && last.role === 'assistant') {
          last.content += toAppend
        } else {
          messages.value.push({ role: 'assistant', content: toAppend, streamComplete: false })
        }
        scrollToBottom()
      },
      onTrace: (line) => {
        if (traceLines.value.length >= MAX_TRACE_LINES) traceLines.value.shift()
        traceLines.value.push(line)
        scrollToBottom()
      },
      onError: (err) => {
        error.value = err.message || 'Request failed'
        const last = messages.value[messages.value.length - 1]
        if (last && last.role === 'assistant') messages.value.pop()
        isLoading.value = false
      },
      onDone: () => {
        isLoading.value = false
        const last = messages.value[messages.value.length - 1]
        if (last?.role === 'assistant') {
          last.streamComplete = true
        }
        scrollToBottom()
        emit('run-complete')
      }
    }
  )
}

/** @param {string} text */
function sendSuggested(text) {
  inputMessage.value = text
  sendMessage()
}
</script>

<style scoped>
.chat-panel {
  display: flex;
  flex-direction: column;
  flex: 1;
  min-height: 0;
  background: #0f172a;
  border-radius: 16px;
  border: 1px solid #1e293b;
  margin: 1rem;
}

.chat-messages {
  flex: 1;
  overflow-y: auto;
  padding: 1.5rem;
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.chat-welcome {
  text-align: center;
  padding: 2.5rem 1rem;
  color: #94a3b8;
}

.welcome-icon {
  margin-bottom: 1.25rem;
}

.welcome-icon svg {
  color: #10b981;
}

.chat-welcome h3 {
  margin: 0 0 0.75rem 0;
  color: #f1f5f9;
  font-size: 1.25rem;
  font-weight: 600;
}

.chat-welcome p {
  margin: 0 0 1.75rem 0;
  font-size: 0.9375rem;
  line-height: 1.6;
  max-width: 420px;
  margin-left: auto;
  margin-right: auto;
}

.suggested-prompts {
  display: flex;
  flex-wrap: wrap;
  gap: 0.625rem;
  justify-content: center;
}

.suggested-prompts button {
  background: #1e293b;
  border: 1px solid #334155;
  color: #e2e8f0;
  padding: 0.625rem 1rem;
  border-radius: 8px;
  font-size: 0.8125rem;
  cursor: pointer;
  transition: all 0.2s;
}

.suggested-prompts button:hover {
  background: #334155;
  border-color: #10b981;
}

.message {
  display: flex;
  gap: 0.75rem;
  max-width: 90%;
}

.message.user {
  align-self: flex-end;
  flex-direction: row-reverse;
}

.message-avatar {
  width: 32px;
  height: 32px;
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.message.user .message-avatar {
  background: #3b82f6;
  color: white;
}

.message.assistant .message-avatar {
  background: #10b981;
  color: white;
}

.message-content {
  background: #1e293b;
  padding: 0.875rem 1rem;
  border-radius: 12px;
  color: #e2e8f0;
  font-size: 0.9375rem;
  line-height: 1.6;
  min-width: 0;
}

.message-toolbar {
  display: flex;
  justify-content: flex-end;
  align-items: center;
  gap: 0.5rem;
  margin: -0.25rem 0 0.5rem;
}

.view-toggle {
  display: inline-flex;
  border: 1px solid #334155;
  border-radius: 6px;
  overflow: hidden;
}

.view-toggle button {
  background: #0f172a;
  border: none;
  color: #94a3b8;
  font-size: 0.6875rem;
  font-weight: 600;
  letter-spacing: 0.02em;
  padding: 0.25rem 0.5rem;
  cursor: pointer;
  text-transform: uppercase;
}

.view-toggle button.active {
  background: #334155;
  color: #f1f5f9;
}

.view-toggle button:not(.active):hover {
  color: #cbd5e1;
}

.copy-btn {
  background: #0f172a;
  border: 1px solid #334155;
  border-radius: 6px;
  color: #94a3b8;
  font-size: 0.6875rem;
  font-weight: 600;
  letter-spacing: 0.02em;
  padding: 0.25rem 0.5rem;
  cursor: pointer;
  text-transform: uppercase;
}

.copy-btn:hover:not(:disabled) {
  color: #cbd5e1;
  border-color: #475569;
}

.copy-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.message-text.plain,
.message-text.user-text {
  margin: 0;
  white-space: pre-wrap;
  word-break: break-word;
  font-family: inherit;
  font-size: inherit;
  line-height: inherit;
  color: inherit;
  background: transparent;
}

.stream-end {
  margin-top: 0.625rem;
  padding-top: 0.5rem;
  border-top: 1px solid #334155;
  color: #64748b;
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
  font-size: 0.6875rem;
  font-weight: 600;
  letter-spacing: 0.08em;
  text-align: right;
}

.message.user .message-content {
  background: #3b82f6;
  color: white;
}

.message-text :deep(pre) {
  background: #0f172a;
  padding: 0.75rem;
  border-radius: 6px;
  overflow-x: auto;
  margin: 0.5rem 0;
}

.message-text :deep(code) {
  background: #334155;
  padding: 0.125rem 0.375rem;
  border-radius: 4px;
  font-family: ui-monospace, monospace;
  font-size: 0.875em;
}

.message-text :deep(pre code) {
  background: transparent;
  padding: 0;
}

.message-text :deep(li) {
  margin-left: 1rem;
}

.message-text.markdown :deep(h1),
.message-text.markdown :deep(h2),
.message-text.markdown :deep(h3),
.message-text.markdown :deep(h4) {
  margin: 0.75rem 0 0.5rem;
  color: #f1f5f9;
  line-height: 1.3;
}

.message-text.markdown :deep(h1:first-child),
.message-text.markdown :deep(h2:first-child),
.message-text.markdown :deep(h3:first-child),
.message-text.markdown :deep(p:first-child) {
  margin-top: 0;
}

.message-text.markdown :deep(p) {
  margin: 0.5rem 0;
}

.message-text.markdown :deep(ul),
.message-text.markdown :deep(ol) {
  margin: 0.5rem 0;
  padding-left: 1.25rem;
}

.message-text.markdown :deep(blockquote) {
  margin: 0.5rem 0;
  padding-left: 0.75rem;
  border-left: 3px solid #475569;
  color: #cbd5e1;
}

.message-text.markdown :deep(a) {
  color: #34d399;
}

.message-text.markdown :deep(table) {
  border-collapse: collapse;
  margin: 0.5rem 0;
  width: 100%;
}

.message-text.markdown :deep(th),
.message-text.markdown :deep(td) {
  border: 1px solid #334155;
  padding: 0.375rem 0.5rem;
}

.typing-indicator {
  display: flex;
  gap: 4px;
  padding: 0.25rem 0;
}

.typing-indicator span {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: #64748b;
  animation: typing 1.4s infinite;
}

.typing-indicator span:nth-child(2) {
  animation-delay: 0.2s;
}

.typing-indicator span:nth-child(3) {
  animation-delay: 0.4s;
}

@keyframes typing {
  0%,
  60%,
  100% {
    transform: translateY(0);
    opacity: 0.4;
  }
  30% {
    transform: translateY(-4px);
    opacity: 1;
  }
}

.chat-error {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  background: #7f1d1d;
  color: #fecaca;
  padding: 0.75rem 1rem;
  border-radius: 8px;
  font-size: 0.875rem;
}

.chat-error button {
  margin-left: auto;
  background: none;
  border: none;
  color: #fecaca;
  cursor: pointer;
  text-decoration: underline;
}

.chat-input-area {
  padding: 1rem 1.25rem;
  border-top: 1px solid #1e293b;
  background: #0f172a;
  border-radius: 0 0 16px 16px;
}

.chat-trace {
  margin: 0 1rem 0.75rem;
  padding: 0.5rem 0.75rem;
  border-radius: 8px;
  border: 1px solid #334155;
  background: #020617;
  font-size: 0.75rem;
  color: #94a3b8;
}

.chat-trace summary {
  cursor: pointer;
  color: #cbd5e1;
  user-select: none;
}

.chat-trace .trace-count {
  color: #64748b;
  font-weight: normal;
}

.chat-trace-pre {
  margin: 0.5rem 0 0;
  max-height: 12rem;
  overflow: auto;
  white-space: pre-wrap;
  word-break: break-word;
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
  font-size: 0.7rem;
  line-height: 1.35;
  color: #a8b8cf;
}

.input-row {
  display: flex;
  gap: 0.75rem;
}

.input-row textarea {
  flex: 1;
  background: #1e293b;
  border: 1px solid #334155;
  border-radius: 10px;
  padding: 0.75rem 1rem;
  color: #f1f5f9;
  font-size: 0.9375rem;
  resize: none;
  min-height: 44px;
  max-height: 120px;
  font-family: inherit;
}

.input-row textarea::placeholder {
  color: #64748b;
}

.input-row textarea:focus {
  outline: none;
  border-color: #10b981;
}

.send-btn {
  background: #10b981;
  border: none;
  border-radius: 10px;
  width: 44px;
  height: 44px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: white;
  cursor: pointer;
  transition: all 0.2s;
}

.send-btn:hover:not(:disabled) {
  background: #059669;
}

.send-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}
</style>
