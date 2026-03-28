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
              @approve-simulation="handleApproveSimulation"
              @approve-trade="handleApproveTrade"
              @reject-trade="handleRejectTrade"
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
              @approve-trade="handleApproveTrade"
              @reject-trade="handleRejectTrade"
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
        <EventFeed />
      </aside>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import {
  startScan, getScanStatus, getOpportunities,
  approveSimulation, approveTrade, rejectTrade,
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

// Split opportunities into simulation-ready and other
const filteredOpps = computed(() => {
  if (!activeFilter.value) return allOpportunities.value
  return allOpportunities.value.filter(o => o.status === activeFilter.value)
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
    await startScan({ limit: 10 })
    // Poll for completion
    pollScan()
  } catch (e) {
    console.error('Scan failed:', e)
    scanStatus.value = 'idle'
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
      }
    } catch {
      clearInterval(interval)
      scanStatus.value = 'idle'
    }
  }, 2000)
}

function goToOpportunity(id) {
  router.push(`/opportunity/${id}`)
}

async function handleApproveSimulation(id) {
  try {
    await approveSimulation(id)
    router.push(`/opportunity/${id}/simulation`)
  } catch (e) {
    console.error('Failed to approve simulation:', e)
  }
}

async function handleApproveTrade(id) {
  try {
    await approveTrade(id)
    await loadOpportunities()
    portfolioPanel.value?.refresh()
  } catch (e) {
    console.error('Failed to approve trade:', e)
  }
}

async function handleRejectTrade(id) {
  try {
    await rejectTrade(id)
    await loadOpportunities()
  } catch (e) {
    console.error('Failed to reject trade:', e)
  }
}

onMounted(async () => {
  await loadOpportunities()
  // Check if a scan is already running
  try {
    const res = await getScanStatus()
    scanStatus.value = res.data.status
    if (res.data.status === 'running') pollScan()
  } catch {}
})
</script>

<style scoped>
.dashboard {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
}

/* Header */
.dashboard-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 24px;
  border-bottom: 1px solid var(--border);
  background: var(--bg-secondary);
}
.header-left {
  display: flex;
  align-items: baseline;
  gap: 16px;
}
.logo {
  font-size: 16px;
  font-weight: 700;
  letter-spacing: 2px;
  color: var(--accent);
  margin: 0;
}
.tagline {
  font-size: 12px;
  color: var(--text-muted);
}
.header-right {
  display: flex;
  align-items: center;
  gap: 12px;
}
.scan-status {
  font-size: 11px;
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
  background: var(--bg-secondary);
  overflow-y: auto;
}
.main-content {
  flex: 1;
  padding: 20px 24px;
  overflow-y: auto;
}
.sidebar-right {
  width: 280px;
  flex-shrink: 0;
  border-left: 1px solid var(--border);
  background: var(--bg-secondary);
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
