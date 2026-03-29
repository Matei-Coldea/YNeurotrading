<template>
  <div class="simulation-view">
    <header class="sim-header">
      <button class="back-btn" @click="goBack">← Dashboard</button>
      <span class="header-logo">NEURO-TRADE</span>
      <span class="header-divider"></span>
      <span class="header-market">{{ truncate(marketQuestion, 55) }}</span>
      <span class="badge" :class="statusBadge">{{ statusText }}</span>
    </header>

    <div v-if="preparing" class="center-state">
      <div class="spinner"></div>
      <h2>Preparing Simulation</h2>
      <p>Generating seed document and simulation parameters from market research...</p>
      <p class="hint">This usually takes 15-30 seconds</p>
    </div>

    <div v-else-if="error" class="center-state">
      <p class="error-msg">{{ error }}</p>
      <button class="btn btn-primary" @click="goBack">Back to Dashboard</button>
    </div>

    <iframe
      v-else-if="iframeUrl"
      :src="iframeUrl"
      class="mirofish-frame"
    ></iframe>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { getOpportunity, startSimulation, syncMirofish } from '../api/agent'

const props = defineProps({ id: String })
const router = useRouter()

const preparing = ref(true)
const error = ref(null)
const iframeUrl = ref(null)
const marketQuestion = ref('')
const oppStatus = ref('')

const statusBadge = computed(() => ({
  'badge-yellow': oppStatus.value === 'simulation_running' || preparing.value,
  'badge-green': oppStatus.value === 'simulation_complete',
}))

const statusText = computed(() => {
  if (preparing.value) return 'Preparing'
  return {
    simulation_running: 'Simulating',
    simulation_complete: 'Complete',
  }[oppStatus.value] || 'Running'
})

onMounted(async () => {
  try {
    const res = await getOpportunity(props.id)
    const opp = res.data.opportunity
    marketQuestion.value = opp.market_question || ''
    oppStatus.value = opp.status

    if (opp.mirofish_project_id) {
      // Already has a project — show iframe directly
      iframeUrl.value = `http://localhost:3000/process/${opp.mirofish_project_id}`
      preparing.value = false
    } else {
      // Create the project, then show iframe
      const simRes = await startSimulation(props.id)
      iframeUrl.value = simRes.data.mirofish_url
      oppStatus.value = 'simulation_running'
      preparing.value = false
    }
  } catch (e) {
    error.value = e.response?.data?.detail || e.message || 'Failed to start simulation'
    preparing.value = false
  }
})

async function goBack() {
  try { await syncMirofish(props.id) } catch {}
  router.push('/')
}

function truncate(s, len) {
  if (!s) return ''
  return s.length > len ? s.slice(0, len) + '...' : s
}
</script>

<style scoped>
.simulation-view {
  height: 100vh;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.sim-header {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 0 16px;
  height: 44px;
  background: #000;
  color: #fff;
  flex-shrink: 0;
}

.back-btn {
  background: none;
  border: 1px solid #444;
  color: #fff;
  font-size: 12px;
  padding: 4px 10px;
  border-radius: 4px;
  cursor: pointer;
  white-space: nowrap;
}
.back-btn:hover {
  background: #222;
}

.header-logo {
  font-family: var(--font-mono);
  font-size: 13px;
  font-weight: 800;
  letter-spacing: 2px;
  white-space: nowrap;
}

.header-divider {
  width: 1px;
  height: 20px;
  background: #444;
  flex-shrink: 0;
}

.header-market {
  font-size: 12px;
  color: #999;
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.mirofish-frame {
  flex: 1;
  width: 100%;
  border: none;
}

.center-state {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 12px;
  text-align: center;
  padding: 40px;
}
.center-state h2 {
  font-size: 18px;
  font-weight: 600;
  color: var(--text-primary);
  margin: 0;
}
.center-state p {
  font-size: 14px;
  color: var(--text-secondary);
  margin: 0;
}
.center-state .hint {
  font-size: 12px;
  color: var(--text-muted);
}
.error-msg {
  color: var(--red);
}

.spinner {
  width: 32px;
  height: 32px;
  border: 3px solid var(--border-light, #e5e5e5);
  border-top-color: var(--accent, #FF4500);
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}
@keyframes spin { to { transform: rotate(360deg); } }
</style>
