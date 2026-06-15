<template>
  <div class="app-root">
    <header v-if="staticSiteUrl" class="top-bar">
      <a class="back-to-site" :href="staticSiteUrl">{{ staticSiteLabel }}</a>
    </header>
    <div class="layout">
    <SessionSidebar
      ref="sidebarRef"
      :team-id="teamId"
      :user-id="userId"
      :selected-session-id="selectedSessionId"
      @select="onSelectSession"
      @new-chat="onNewChat"
      @update:user-id="onUserId"
    />
    <main class="main">
      <KmChatPanel
        v-if="chatReady"
        :team-id="teamId"
        :user-id="userId"
        @run-complete="onRunComplete"
      />
      <p v-else class="boot-msg">Connecting to AgentOS…</p>
    </main>
    </div>
  </div>
</template>

<script setup>
/**
 * Main layout: optional static-site link, session sidebar, and chat panel.
 * Resolves agent id from AgentOS on mount; keeps user_id in route + localStorage.
 */
import { ref, computed, onMounted, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import SessionSidebar from '@/components/SessionSidebar.vue'
import KmChatPanel from '@/components/KmChatPanel.vue'
import { listTeams, pickTeamId } from '@/services/agentOs.js'

const STORAGE_KEY = 'km_agno_user_id'

/** Full URL to static docs/site (MkDocs, studies site). Empty hides the header link. */
const staticSiteUrl = computed(() => {
  const v = import.meta.env.VITE_STATIC_SITE_URL
  return typeof v === 'string' && v.trim() !== '' ? v.trim() : ''
})

const staticSiteLabel = computed(() => {
  const v = import.meta.env.VITE_STATIC_SITE_LABEL
  return typeof v === 'string' && v.trim() !== '' ? v.trim() : 'Back to studies'
})

const route = useRoute()
const router = useRouter()
const sidebarRef = ref(null)
const teamId = ref('kma')
const chatReady = ref(false)

const userId = ref('local')

const selectedSessionId = computed(() => {
  const s = route.query.session_id
  return s != null && String(s).trim() !== '' ? String(s).trim() : ''
})

/** Read user_id from route or localStorage; write back to route when missing. */
function syncUserFromRouteAndStorage() {
  const q = route.query.user_id
  if (q != null && String(q).trim() !== '') {
    userId.value = String(q).trim()
    try {
      localStorage.setItem(STORAGE_KEY, userId.value)
    } catch {
      /* ignore */
    }
    return
  }
  try {
    const s = localStorage.getItem(STORAGE_KEY)
    if (s != null && s.trim() !== '') {
      userId.value = s.trim()
    }
  } catch {
    /* ignore */
  }
  router.replace({
    query: {
      ...route.query,
      user_id: userId.value
    }
  })
}

/** @param {string} v */
function onUserId(v) {
  userId.value = v && v.trim() !== '' ? v.trim() : 'local'
  try {
    localStorage.setItem(STORAGE_KEY, userId.value)
  } catch {
    /* ignore */
  }
  router.replace({
    query: {
      ...route.query,
      user_id: userId.value
    }
  })
}

/** @param {string} sessionId */
function onSelectSession(sessionId) {
  router.replace({
    query: {
      user_id: userId.value,
      session_id: sessionId
    }
  })
}

/** Clear session_id in the URL to start a fresh conversation. */
function onNewChat() {
  router.replace({
    query: {
      user_id: userId.value
    }
  })
}

/** After a streamed run finishes, refresh the sidebar session list. */
function onRunComplete() {
  sidebarRef.value?.refreshList?.()
}

watch(
  () => route.query.user_id,
  () => {
    syncUserFromRouteAndStorage()
  }
)

onMounted(async () => {
  document.title = 'Expert Agent — Flink Studies'
  syncUserFromRouteAndStorage()
  try {
    const teams = await listTeams()
    teamId.value = pickTeamId(teams)
  } catch {
    teamId.value = 'kma'
  }
  chatReady.value = true
})
</script>

<style scoped>
.app-root {
  display: flex;
  flex-direction: column;
  height: 100%;
  min-height: 0;
}

.top-bar {
  flex-shrink: 0;
  display: flex;
  align-items: center;
  padding: 0.5rem 1rem;
  background: #020617;
  border-bottom: 1px solid #1e293b;
}

.back-to-site {
  display: inline-flex;
  align-items: center;
  gap: 0.375rem;
  padding: 0.375rem 0.75rem;
  border-radius: 8px;
  border: 1px solid #334155;
  background: #1e293b;
  color: #e2e8f0;
  font-size: 0.8125rem;
  font-weight: 500;
  text-decoration: none;
}

.back-to-site:hover {
  border-color: #10b981;
  color: #10b981;
}

.layout {
  display: flex;
  flex: 1;
  min-height: 0;
}

.main {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-width: 0;
  min-height: 0;
}

.boot-msg {
  margin: auto;
  color: #64748b;
  font-size: 0.9375rem;
}
</style>
