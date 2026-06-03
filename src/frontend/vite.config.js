/**
 * Vite config: Vue plugin, `@` alias, dev server port, and `/agent-os` proxy to AgentOS.
 */
import { defineConfig, loadEnv } from 'vite'
import vue from '@vitejs/plugin-vue'
import { fileURLToPath, URL } from 'node:url'

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), '')
  const agentOsTarget =
    env.VITE_AGENT_OS_ORIGIN || env.AGENT_OS_ORIGIN || 'http://127.0.0.1:8000'

  return {
    plugins: [vue()],
    resolve: {
      alias: {
        '@': fileURLToPath(new URL('./src', import.meta.url))
      }
    },
    server: {
      port: parseInt(env.KMA_VITE_PORT || env.VITE_PORT || '5174', 10),
      host: true,
      proxy: {
        '/agent-os': {
          target: agentOsTarget,
          changeOrigin: true,
          rewrite: (path) => path.replace(/^\/agent-os/, '')
        }
      }
    }
  }
})
