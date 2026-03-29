<template>
  <div class="dashboard">
    <!-- Header -->
    <header class="dashboard-header">
      <div class="header-left">
        <h1 class="logo">NEURO-TRADE</h1>
        <span class="tagline">Simulation-Enhanced Prediction Market Trading</span>
      </div>
      <div class="header-right">
        <span class="scan-status badge" :class="scanStatusClass">{{ scanStatusText }}</span>
        <button class="btn btn-primary" @click="triggerScan" :disabled="scanStatus === 'running'">
          {{ scanStatus === 'running' ? 'Scanning...' : 'Scan Markets' }}
        </button>
      </div>
    </header>

    <!-- Main Layout -->
    <div class="dashboard-body">
      <!-- Left: Pipeline Funnel -->
      <aside class="sidebar-left">
        <PipelineFunnel
          :opportunities="allOpportunities"
          :active-filter="activeFilter"
          @filter="activeFilter = $event"
        />
      </aside>

      <!-- Center: Opportunities -->
      <main class="main-content">

        <!-- Simulation-Ready Markets -->
        <section v-if="simReadyOpps.length" class="market-section">
          <h2 class="section-title">Simulation-Ready Markets</h2>
          <div class="opp-grid">
            <OpportunityCard
              v-for="opp in simReadyOpps"
              :key="opp.id"
              :opp="opp"
              @select="goToOpportunity"
              @start-simulation="handleStartSimulation"
              @analyze-report="handleAnalyzeReport"
              @approve-trade="handleApproveTrade"
              @reject-trade="handleRejectTrade"
              @manual-trade="handleManualTrade"
            />
          </div>
        </section>

        <!-- Other Markets (collapsed by default) -->
        <section v-if="otherOpps.length" class="market-section">
          <button class="section-toggle" @click="showOther = !showOther">
            <span>Other Markets ({{ otherOpps.length }})</span>
            <span class="toggle-arrow" :class="{ open: showOther }">▸</span>
          </button>
          <div v-if="showOther" class="opp-grid">
            <OpportunityCard
              v-for="opp in otherOpps"
              :key="opp.id"
              :opp="opp"
              @select="goToOpportunity"
              @start-simulation="handleStartSimulation"
              @analyze-report="handleAnalyzeReport"
              @approve-trade="handleApproveTrade"
              @reject-trade="handleRejectTrade"
              @manual-trade="handleManualTrade"
            />
          </div>
        </section>

        <div v-if="!allOpportunities.length && scanStatus !== 'running'" class="empty-state">
          <p>No markets discovered yet.</p>
          <p class="text-muted">Click "Scan Markets" to find sentiment-driven prediction markets.</p>
        </div>
      </main>

      <!-- Right: Portfolio + Events -->
      <aside class="sidebar-right">
        <PortfolioPanel ref="portfolioPanel" />
        <div class="sidebar-divider"></div>
        <EventFeed ref="eventFeedRef" />
      </aside>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import {
  startScan, getScanStatus, getOpportunities, deduplicate,
  analyzeReport, approveTrade, rejectTrade, manualTrade, refreshPrices,
} from '../api/agent'
import PipelineFunnel from '../components/PipelineFunnel.vue'
import OpportunityCard from '../components/OpportunityCard.vue'
import PortfolioPanel from '../components/PortfolioPanel.vue'
import EventFeed from '../components/EventFeed.vue'

const router = useRouter()
const allOpportunities = ref([])
const scanStatus = ref('idle')
const activeFilter = ref(null)
const showOther = ref(false)
const portfolioPanel = ref(null)
const eventFeedRef = ref(null)

// Split opportunities into simulation-ready and other
const filteredOpps = computed(() => {
  if (!activeFilter.value) return allOpportunities.value
  // Match grouped statuses (same groups as PipelineFunnel counts)
  const statusGroups = {
    simulation_running: ['simulation_running', 'simulation_approved'],
    trade_executed: ['trade_executed', 'trade_approved'],
  }
  const statuses = statusGroups[activeFilter.value] || [activeFilter.value]
  return allOpportunities.value.filter(o => statuses.includes(o.status))
})

const simReadyOpps = computed(() =>
  filteredOpps.value.filter(o => (o.simulation_potential || 0) >= 3)
)

const otherOpps = computed(() =>
  filteredOpps.value.filter(o => (o.simulation_potential || 0) < 3)
)

const scanStatusClass = computed(() => ({
  'badge-yellow': scanStatus.value === 'running',
  'badge-green': scanStatus.value === 'complete',
  'badge-blue': scanStatus.value === 'idle',
}))

const scanStatusText = computed(() => ({
  running: 'Scanning',
  complete: 'Ready',
  idle: 'Idle',
}[scanStatus.value] || 'Idle'))

async function loadOpportunities() {
  try {
    const res = await getOpportunities()
    allOpportunities.value = res.data.opportunities || []
  } catch (e) {
    console.error('Failed to load opportunities:', e)
  }
}

async function triggerScan() {
  try {
    scanStatus.value = 'running'
    eventFeedRef.value?.addEvent('scan_started')
    await startScan({ limit: 10 })
    pollScan()
  } catch (e) {
    console.error('Scan failed:', e)
    scanStatus.value = 'idle'
    eventFeedRef.value?.addEvent('error', { message: 'Scan failed' })
  }
}

async function pollScan() {
  const interval = setInterval(async () => {
    try {
      const res = await getScanStatus()
      scanStatus.value = res.data.status
      if (res.data.status === 'complete' || res.data.status === 'idle') {
        clearInterval(interval)
        await loadOpportunities()
        if (res.data.status === 'complete') {
          eventFeedRef.value?.addEvent('scan_complete', { opportunities_found: res.data.opportunities_found || allOpportunities.value.length })
        }
      }
    } catch {
      clearInterval(interval)
      scanStatus.value = 'idle'
    }
  }, 2000)
}

function goToOpportunity(id) {
  const opp = allOpportunities.value.find(o => o.id === id)
  if (!opp) { router.push(`/opportunity/${id}`); return }
  if (['simulation_running', 'simulation_approved'].includes(opp.status)) {
    router.push(`/opportunity/${id}/simulation`)
  } else if (['simulation_complete', 'trade_proposed'].includes(opp.status)) {
    router.push(`/opportunity/${id}/trade`)
  } else {
    router.push(`/opportunity/${id}`)
  }
}

function handleStartSimulation(id) {
  router.push(`/opportunity/${id}/simulation`)
}

async function handleAnalyzeReport(id) {
  try {
    eventFeedRef.value?.addEvent('report_started', { market_question: allOpportunities.value.find(o => o.id === id)?.market_question })
    await analyzeReport(id)
    await loadOpportunities()
    eventFeedRef.value?.addEvent('trade_proposed')
  } catch (e) {
    console.error('Failed to analyze report:', e)
    eventFeedRef.value?.addEvent('error', { message: 'Analysis failed' })
  }
}

async function handleApproveTrade(id) {
  try {
    await approveTrade(id)
    await loadOpportunities()
    portfolioPanel.value?.refresh()
    eventFeedRef.value?.addEvent('trade_approved')
  } catch (e) {
    console.error('Failed to approve trade:', e)
  }
}

async function handleRejectTrade(id) {
  try {
    await rejectTrade(id)
    await loadOpportunities()
    eventFeedRef.value?.addEvent('trade_rejected')
  } catch (e) {
    console.error('Failed to reject trade:', e)
  }
}

async function handleManualTrade({ id, outcome, amount }) {
  try {
    const result = await manualTrade(id, { side: 'buy', outcome, amount_usd: amount || 50 })
    await loadOpportunities()
    portfolioPanel.value?.refresh()
    eventFeedRef.value?.addEvent('trade_executed', {
      side: 'buy', outcome,
      shares: result.data?.shares, avg_price: result.data?.price,
    })
  } catch (e) {
    console.error('Manual trade failed:', e)
    eventFeedRef.value?.addEvent('error', { message: 'Trade failed' })
  }
}

let priceTimer = null

onMounted(async () => {
  // Clean up any existing duplicates, then load
  deduplicate().catch(() => {})
  await loadOpportunities()

  // Refresh prices in background, then reload
  refreshPrices().then(() => loadOpportunities()).catch(() => {})

  // Auto-refresh prices every 30s
  priceTimer = setInterval(async () => {
    try {
      await refreshPrices()
      await loadOpportunities()
    } catch {}
  }, 30000)

  // Check if a scan is already running
  try {
    const res = await getScanStatus()
    scanStatus.value = res.data.status
    if (res.data.status === 'running') pollScan()
  } catch {}
})

onUnmounted(() => {
  if (priceTimer) clearInterval(priceTimer)
})
</script>

<style scoped>
.dashboard {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
}

/* Header — matches MiroFish navbar */
.dashboard-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 24px;
  height: 60px;
  background: #000;
  color: #fff;
}
.header-left {
  display: flex;
  align-items: baseline;
  gap: 16px;
}
.logo {
  font-family: var(--font-mono);
  font-size: 16px;
  font-weight: 800;
  letter-spacing: 2px;
  color: #fff;
  margin: 0;
}
.tagline {
  font-size: 0.75rem;
  color: #999;
}
.header-right {
  display: flex;
  align-items: center;
  gap: 12px;
}
.header-right .btn-primary {
  background: var(--accent);
  border-color: var(--accent);
}
.header-right .btn-primary:hover {
  background: var(--accent-hover);
}
.scan-status {
  font-size: 0.7rem;
}

/* Body Layout */
.dashboard-body {
  display: flex;
  flex: 1;
  min-height: 0;
}
.sidebar-left {
  width: 200px;
  flex-shrink: 0;
  border-right: 1px solid var(--border);
  background: var(--bg-primary);
  overflow-y: auto;
}
.main-content {
  flex: 1;
  padding: 20px 24px;
  overflow-y: auto;
  background: var(--bg-secondary);
}
.sidebar-right {
  width: 280px;
  flex-shrink: 0;
  border-left: 1px solid var(--border);
  background: var(--bg-primary);
  overflow-y: auto;
}
.sidebar-divider {
  height: 1px;
  background: var(--border);
  margin: 0 16px;
}

/* Sections */
.section-title {
  font-size: 14px;
  font-weight: 600;
  color: var(--text-secondary);
  margin-bottom: 12px;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}
.market-section {
  margin-bottom: 24px;
}
.opp-grid {
  display: flex;
  flex-direction: column;
  gap: 12px;
}
.section-toggle {
  display: flex;
  align-items: center;
  gap: 8px;
  background: none;
  border: none;
  color: var(--text-muted);
  font-size: 13px;
  cursor: pointer;
  padding: 8px 0;
  margin-bottom: 8px;
}
.section-toggle:hover {
  color: var(--text-secondary);
}
.toggle-arrow {
  transition: transform 0.2s;
}
.toggle-arrow.open {
  transform: rotate(90deg);
}

/* Empty state */
.empty-state {
  text-align: center;
  padding: 60px 20px;
  color: var(--text-secondary);
}
.empty-state p {
  margin-bottom: 8px;
}
</style>
