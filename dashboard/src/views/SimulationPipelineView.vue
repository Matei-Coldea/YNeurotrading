<template>
  <div class="simulation-view">
    <header class="sim-header">
      <button class="back-btn" @click="showIframe ? exitFullscreen() : goBack()">
        {{ showIframe ? '← Overview' : '← Dashboard' }}
      </button>
      <span class="header-logo">NEURO-TRADE</span>
      <span class="header-divider"></span>
      <span class="header-market">{{ truncate(marketQuestion, 55) }}</span>
      <span class="badge" :class="statusBadge">{{ statusText }}</span>
    </header>

    <!-- Preparing state (generating seed doc) -->
    <div v-if="preparing" class="center-state">
      <div class="spinner"></div>
      <h2>Preparing Simulation</h2>
      <p>Generating seed document and simulation parameters...</p>
      <p class="hint">This usually takes 15-30 seconds</p>
    </div>

    <!-- Error state -->
    <div v-else-if="error" class="center-state">
      <p class="error-msg">{{ error }}</p>
      <button class="btn btn-primary" @click="goBack">Back to Dashboard</button>
    </div>

    <!-- Status overview (default view) -->
    <div v-show="!showIframe && !preparing && !error" class="status-body">
      <div class="overview-grid">
        <!-- Progress panel -->
        <div class="panel card">
          <h3 class="panel-title">Simulation Progress</h3>

          <div class="step-list">
            <div class="step-row">
              <span class="step-icon" :class="{ done: opp?.mirofish_project_id }">{{ opp?.mirofish_project_id ? '✓' : '○' }}</span>
              <span>Environment Setup</span>
            </div>
            <div class="step-row">
              <span class="step-icon" :class="{ done: opp?.mirofish_simulation_id, active: opp?.mirofish_project_id && !opp?.mirofish_simulation_id }">
                {{ opp?.mirofish_simulation_id ? '✓' : opp?.mirofish_project_id ? '◉' : '○' }}
              </span>
              <span>Ontology &amp; Knowledge Graph</span>
            </div>
            <div class="step-row">
              <span class="step-icon" :class="{ done: isSimComplete, active: opp?.mirofish_simulation_id && !isSimComplete }">
                {{ isSimComplete ? '✓' : opp?.mirofish_simulation_id ? '◉' : '○' }}
              </span>
              <span>Social Simulation</span>
              <span v-if="simProgress.current_round" class="step-detail font-mono">
                Round {{ simProgress.current_round }}/{{ simProgress.total_rounds || '?' }}
              </span>
            </div>
            <div class="step-row">
              <span class="step-icon" :class="{ done: !!opp?.mirofish_report_id, active: generatingReport }">
                {{ opp?.mirofish_report_id ? '✓' : generatingReport ? '◉' : '○' }}
              </span>
              <span>Analysis Report</span>
              <span v-if="generatingReport && reportProgress?.sections_done" class="step-detail font-mono">
                {{ reportProgress.sections_done }}/{{ reportProgress.sections_total || '?' }}
              </span>
            </div>
          </div>

          <div v-if="progressPercent > 0" class="progress-wrap">
            <div class="progress-track">
              <div class="progress-fill" :style="{ width: progressPercent + '%' }"></div>
            </div>
            <span class="progress-pct font-mono">{{ progressPercent }}%</span>
          </div>

          <div v-if="simProgress.twitter_actions_count" class="stat-row">
            <span class="stat-label">Posts generated</span>
            <span class="stat-val font-mono">{{ simProgress.twitter_actions_count }}</span>
          </div>

          <button class="btn btn-primary open-btn" @click="enterFullscreen">
            Open Full Simulation
          </button>

          <div class="quick-links">
            <a v-if="opp?.mirofish_simulation_id"
               :href="`http://localhost:3000/y/${opp.mirofish_simulation_id}`"
               target="_blank" class="link-btn">Live Feed ↗</a>
            <a v-if="opp?.mirofish_report_id"
               :href="`http://localhost:3000/report/${opp.mirofish_report_id}`"
               target="_blank" class="link-btn">Report ↗</a>
          </div>
        </div>

        <!-- Market context panel -->
        <div class="panel card">
          <h3 class="panel-title">Market Context</h3>
          <h4 class="market-q">{{ opp?.market_question }}</h4>
          <div class="prices-row">
            <div class="price-box">
              <span class="lbl">Yes</span>
              <span class="pval font-mono">${{ formatPrice(opp?.outcome_prices?.[0]) }}</span>
            </div>
            <div class="price-box">
              <span class="lbl">No</span>
              <span class="pval font-mono">${{ formatPrice(opp?.outcome_prices?.[1]) }}</span>
            </div>
            <div v-if="opp?.estimated_edge != null" class="price-box">
              <span class="lbl">Edge</span>
              <span class="pval font-mono" :class="opp.estimated_edge > 0 ? 'text-green' : 'text-red'">
                {{ opp.estimated_edge > 0 ? '+' : '' }}{{ (opp.estimated_edge * 100).toFixed(1) }}pp
              </span>
            </div>
          </div>
          <p v-if="opp?.agent_hypothesis" class="hyp-text">{{ opp.agent_hypothesis }}</p>
          <p v-if="opp?.simulation_rationale" class="rat-text">{{ opp.simulation_rationale }}</p>
        </div>

        <!-- Recent simulation posts -->
        <div v-if="recentPosts.length" class="panel card full-width">
          <h3 class="panel-title">Recent Simulation Activity</h3>
          <div class="posts-feed">
            <div v-for="(post, i) in recentPosts" :key="i" class="post-item">
              <div class="post-meta">
                <span class="post-author">@{{ post.author_username || post.agent_name || 'agent' }}</span>
                <span v-if="post.created_at" class="post-time text-muted">{{ formatTime(post.created_at) }}</span>
              </div>
              <p class="post-text">{{ post.content || post.text || post.body }}</p>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Iframe — v-show keeps it alive when toggling back to overview -->
    <iframe
      v-if="iframeUrl"
      v-show="showIframe"
      :src="iframeUrl"
      class="mirofish-frame"
    ></iframe>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import { getOpportunity, startSimulation, syncMirofish } from '../api/agent'
import { getRunStatus, getPostsFeed, generateReport, getReportGenerationStatus } from '../api/mirofish'

const props = defineProps({ id: String })
const router = useRouter()

const preparing = ref(true)
const error = ref(null)
const opp = ref(null)
const showIframe = ref(false)
const iframeUrl = ref(null)
const simProgress = ref({})
const recentPosts = ref([])
const generatingReport = ref(false)
const reportProgress = ref(null)
let pollTimer = null

const marketQuestion = computed(() => opp.value?.market_question || '')

// Pick the deepest MiroFish URL based on current progress
function pickMirofishUrl(opportunity, progress = {}) {
  const { mirofish_project_id, mirofish_simulation_id, mirofish_report_id } = opportunity
  const base = 'http://localhost:3000'

  // Report ready → report view
  if (mirofish_report_id) return `${base}/report/${mirofish_report_id}`

  if (mirofish_simulation_id) {
    const s = progress.runner_status
    // Simulation has been started (running, completed, etc.) → running view
    if (s || progress.current_round > 0) return `${base}/simulation/${mirofish_simulation_id}/start`
    // Simulation created but not started → preparation view
    return `${base}/simulation/${mirofish_simulation_id}`
  }

  // Only project exists → process wizard
  if (mirofish_project_id) return `${base}/process/${mirofish_project_id}`
  return null
}

const isSimComplete = computed(() => {
  const s = simProgress.value.runner_status
  return s === 'completed' || s === 'complete' || s === 'done' || s === 'stopped'
})

const statusBadge = computed(() => ({
  'badge-yellow': !isSimComplete.value && !opp.value?.mirofish_report_id,
  'badge-green': !!opp.value?.mirofish_report_id || opp.value?.status === 'simulation_complete',
}))

const statusText = computed(() => {
  if (preparing.value) return 'Preparing'
  if (opp.value?.mirofish_report_id || opp.value?.status === 'simulation_complete') return 'Complete'
  if (isSimComplete.value) return 'Sim Done'
  if (opp.value?.mirofish_simulation_id) return 'Simulating'
  if (opp.value?.mirofish_project_id) return 'Setting Up'
  return 'Running'
})

const progressPercent = computed(() => {
  const { current_round, total_rounds } = simProgress.value
  if (!current_round || !total_rounds) return 0
  return Math.min(100, Math.round((current_round / total_rounds) * 100))
})

onMounted(async () => {
  try {
    // Sync status from MiroFish first
    try { await syncMirofish(props.id) } catch {}

    const res = await getOpportunity(props.id)
    opp.value = res.data.opportunity

    if (opp.value.mirofish_project_id) {
      // Fetch current progress to pick the right MiroFish URL
      let progress = {}
      if (opp.value.mirofish_simulation_id) {
        try {
          const statusRes = await getRunStatus(opp.value.mirofish_simulation_id)
          progress = statusRes.data?.data || statusRes.data || {}
          simProgress.value = progress
        } catch {}
      }
      iframeUrl.value = pickMirofishUrl(opp.value, progress)
      preparing.value = false
      startPolling()
    } else {
      // Need to create project first
      const simRes = await startSimulation(props.id)
      iframeUrl.value = simRes.data.mirofish_url
      const res2 = await getOpportunity(props.id)
      opp.value = res2.data.opportunity
      preparing.value = false
      startPolling()
    }
  } catch (e) {
    error.value = e.response?.data?.detail || e.message || 'Failed to start simulation'
    preparing.value = false
  }
})

function startPolling() {
  fetchProgress()
  pollTimer = setInterval(fetchProgress, 5000)
}

async function fetchProgress() {
  const simId = opp.value?.mirofish_simulation_id
  if (!simId) {
    // No simulation_id yet — sync to check if one was created in MiroFish
    try {
      await syncMirofish(props.id)
      const res = await getOpportunity(props.id)
      opp.value = res.data.opportunity
    } catch {}
    return
  }

  // Fetch live progress directly from MiroFish
  try {
    const statusRes = await getRunStatus(simId)
    simProgress.value = statusRes.data?.data || statusRes.data || {}
  } catch {}

  // Fetch recent posts
  try {
    const postsRes = await getPostsFeed(simId, 5)
    const data = postsRes.data?.data || postsRes.data
    recentPosts.value = (Array.isArray(data) ? data : data?.posts || data?.items || []).slice(0, 5)
  } catch {}

  // When simulation completes, sync agent server status
  if (isSimComplete.value && opp.value?.status !== 'simulation_complete') {
    try {
      await syncMirofish(props.id)
      const res = await getOpportunity(props.id)
      opp.value = res.data.opportunity
    } catch {}
  }

  // Stop polling once fully complete
  if (opp.value?.status === 'simulation_complete') {
    if (pollTimer) { clearInterval(pollTimer); pollTimer = null }
  }
}

async function handleGenerateReport() {
  const simId = opp.value?.mirofish_simulation_id
  if (!simId) return

  generatingReport.value = true
  try {
    const res = await generateReport(simId)
    const data = res.data?.data || res.data
    const taskId = data.task_id

    // Poll for completion
    if (taskId) {
      while (true) {
        await new Promise(r => setTimeout(r, 3000))
        try {
          const statusRes = await getReportGenerationStatus(taskId, simId)
          const sd = statusRes.data?.data || statusRes.data
          reportProgress.value = sd
          if (['completed', 'complete', 'done'].includes(sd.status)) break
          if (['failed', 'error'].includes(sd.status)) throw new Error('Report generation failed')
        } catch (e) {
          if (e.message === 'Report generation failed') throw e
          break
        }
      }
    }

    // Sync to pick up report_id
    await syncMirofish(props.id)
    const oppRes = await getOpportunity(props.id)
    opp.value = oppRes.data.opportunity

    // Update iframe to show report
    if (opp.value.mirofish_report_id) {
      iframeUrl.value = `http://localhost:3000/report/${opp.value.mirofish_report_id}`
    }
  } catch (e) {
    console.error('Report generation failed:', e)
  } finally {
    generatingReport.value = false
  }
}

function enterFullscreen() { showIframe.value = true }

function exitFullscreen() {
  showIframe.value = false
  fetchProgress()
}

async function goBack() {
  try { await syncMirofish(props.id) } catch {}
  router.push('/')
}

function formatPrice(p) { return p ? parseFloat(p).toFixed(2) : '—' }
function formatTime(ts) {
  if (!ts) return ''
  return new Date(ts).toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' })
}
function truncate(s, len) {
  if (!s) return ''
  return s.length > len ? s.slice(0, len) + '...' : s
}

onUnmounted(() => {
  if (pollTimer) clearInterval(pollTimer)
})
</script>

<style scoped>
.simulation-view {
  height: 100vh;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

/* Header */
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
.back-btn:hover { background: #222; }
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

/* Center state (preparing / error) */
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
.center-state h2 { font-size: 18px; font-weight: 600; color: var(--text-primary); margin: 0; }
.center-state p { font-size: 14px; color: var(--text-secondary); margin: 0; }
.center-state .hint { font-size: 12px; color: var(--text-muted); }
.error-msg { color: var(--red); }
.spinner {
  width: 32px; height: 32px;
  border: 3px solid var(--border-light, #e5e5e5);
  border-top-color: var(--accent, #FF4500);
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}
@keyframes spin { to { transform: rotate(360deg); } }

/* Status overview */
.status-body {
  flex: 1;
  overflow-y: auto;
  padding: 24px;
}
.overview-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 16px;
  max-width: 900px;
  margin: 0 auto;
}
.full-width { grid-column: 1 / -1; }
.panel { padding: 20px; }
.panel-title {
  font-size: 12px;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  color: var(--text-muted);
  margin: 0 0 16px 0;
}

/* Step list */
.step-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
  margin-bottom: 16px;
}
.step-row {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 13px;
  color: var(--text-secondary);
}
.step-icon {
  width: 18px;
  text-align: center;
  font-size: 12px;
  color: var(--text-muted);
  flex-shrink: 0;
}
.step-icon.done { color: var(--green, #4caf50); }
.step-icon.active { color: var(--accent, #FF4500); font-weight: 700; }
.step-detail {
  margin-left: auto;
  font-size: 12px;
  color: var(--text-muted);
}

/* Progress bar */
.progress-wrap {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 12px;
}
.progress-track {
  flex: 1;
  height: 6px;
  background: var(--bg-secondary, #f5f5f5);
  border-radius: 3px;
  overflow: hidden;
}
.progress-fill {
  height: 100%;
  background: var(--accent, #FF4500);
  border-radius: 3px;
  transition: width 0.5s ease;
}
.progress-pct {
  font-size: 11px;
  color: var(--text-muted);
  width: 32px;
  text-align: right;
}

/* Stats */
.stat-row {
  display: flex;
  justify-content: space-between;
  font-size: 13px;
  margin-bottom: 16px;
}
.stat-label { color: var(--text-muted); }
.stat-val { font-weight: 600; }

/* Report generation */
.report-gen {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 12px;
  background: var(--yellow-dim, #fff8e1);
  border: 1px solid var(--yellow, #FF9800);
  border-radius: 6px;
  font-size: 13px;
  color: var(--text-secondary);
  margin-bottom: 10px;
}
.spinner-sm {
  display: inline-block;
  width: 14px;
  height: 14px;
  border: 2px solid rgba(0,0,0,0.1);
  border-top-color: var(--accent, #FF4500);
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
  flex-shrink: 0;
}

/* Open button */
.open-btn { width: 100%; margin-bottom: 10px; }

/* Quick links */
.quick-links { display: flex; gap: 12px; }
.link-btn {
  font-size: 12px;
  color: var(--accent, #FF4500);
  text-decoration: none;
}
.link-btn:hover { text-decoration: underline; }

/* Market context */
.market-q {
  font-size: 16px;
  font-weight: 600;
  color: var(--text-primary);
  margin: 0 0 12px 0;
  line-height: 1.35;
}
.prices-row { display: flex; gap: 20px; margin-bottom: 12px; }
.price-box { display: flex; flex-direction: column; gap: 2px; }
.lbl { font-size: 11px; text-transform: uppercase; color: var(--text-muted); }
.pval { font-size: 18px; font-weight: 600; }
.hyp-text { font-size: 13px; color: var(--text-secondary); line-height: 1.5; margin: 0 0 6px 0; }
.rat-text { font-size: 12px; color: var(--text-muted); font-style: italic; margin: 0; }

/* Posts feed */
.posts-feed { display: flex; flex-direction: column; gap: 0; }
.post-item {
  padding: 10px 0;
  border-bottom: 1px solid var(--border-light, #e5e5e5);
}
.post-item:last-child { border-bottom: none; }
.post-meta { display: flex; justify-content: space-between; margin-bottom: 4px; }
.post-author { font-size: 12px; font-weight: 600; color: var(--text-primary); }
.post-time { font-size: 11px; }
.post-text { font-size: 13px; color: var(--text-secondary); line-height: 1.4; margin: 0; }

/* Iframe */
.mirofish-frame {
  flex: 1;
  width: 100%;
  border: none;
}
</style>
