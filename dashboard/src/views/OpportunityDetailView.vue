<template>
  <div class="detail-view">
    <header class="detail-header">
      <button class="btn btn-sm" @click="$router.push('/')">← Back</button>
      <h1 class="logo">NEURO-TRADE</h1>
    </header>

    <div v-if="opp" class="detail-body">
      <!-- Market Overview -->
      <section class="detail-section">
        <h2>Market Overview</h2>
        <div class="card">
          <div class="detail-badge-row">
            <span class="badge" :class="statusBadgeClass">{{ opp.status }}</span>
            <span v-if="opp.tags?.length" v-for="tag in opp.tags" :key="tag" class="badge badge-blue">{{ tag }}</span>
          </div>
          <h3 class="market-q">{{ opp.market_question }}</h3>
          <p v-if="opp.market_description" class="market-desc text-secondary">{{ opp.market_description }}</p>

          <div class="price-row">
            <div class="price-box">
              <span class="price-label">Yes</span>
              <span class="price-val font-mono">${{ formatPrice(opp.outcome_prices?.[0]) }}</span>
            </div>
            <div class="price-box">
              <span class="price-label">No</span>
              <span class="price-val font-mono">${{ formatPrice(opp.outcome_prices?.[1]) }}</span>
            </div>
            <div class="price-box">
              <span class="price-label">Agent Est.</span>
              <span class="price-val font-mono">{{ opp.probability_estimate != null ? (opp.probability_estimate * 100).toFixed(1) + '%' : '—' }}</span>
            </div>
            <div v-if="opp.estimated_edge != null" class="price-box">
              <span class="price-label">Edge</span>
              <span class="price-val font-mono" :class="opp.estimated_edge > 0 ? 'text-green' : 'text-red'">
                {{ opp.estimated_edge > 0 ? '+' : '' }}{{ (opp.estimated_edge * 100).toFixed(1) }}pp
              </span>
            </div>
          </div>

          <div class="meta-row">
            <span v-if="opp.volume">Volume: ${{ formatNumber(opp.volume) }}</span>
            <span v-if="opp.liquidity">Liquidity: ${{ formatNumber(opp.liquidity) }}</span>
            <span v-if="opp.end_date">Ends: {{ opp.end_date }}</span>
          </div>
        </div>
      </section>

      <!-- Agent Analysis -->
      <section class="detail-section">
        <h2>Agent Analysis</h2>
        <div class="card">
          <p v-if="opp.agent_hypothesis" class="analysis-text">{{ opp.agent_hypothesis }}</p>
          <p v-if="opp.simulation_rationale" class="sim-rationale"><strong>Simulation rationale:</strong> {{ opp.simulation_rationale }}</p>
        </div>
      </section>

      <!-- Web Research -->
      <section v-if="opp.web_research_summary" class="detail-section">
        <h2>Web Research</h2>
        <div class="card">
          <p class="research-text">{{ opp.web_research_summary }}</p>
        </div>
      </section>

      <!-- Simulation Results -->
      <section v-if="opp.simulation_report_summary" class="detail-section">
        <h2>Simulation Results</h2>
        <div class="card">
          <p>{{ opp.simulation_report_summary }}</p>
          <div v-if="opp.simulation_sentiment" class="sentiment-row">
            <div v-for="(val, key) in opp.simulation_sentiment" :key="key" class="sentiment-item">
              <span class="sentiment-label">{{ key }}</span>
              <div class="sentiment-bar">
                <div class="sentiment-fill" :style="{ width: (val * 100) + '%' }" :class="sentimentColor(key)"></div>
              </div>
              <span class="sentiment-val font-mono">{{ (val * 100).toFixed(0) }}%</span>
            </div>
          </div>
        </div>
      </section>

      <!-- Trade Proposal -->
      <section v-if="opp.trade_reasoning" class="detail-section">
        <h2>Trade Proposal</h2>
        <div class="card">
          <p>{{ opp.trade_reasoning }}</p>
          <div v-if="opp.trade_side && opp.trade_side !== 'skip'" class="trade-summary">
            <span>{{ opp.trade_side.toUpperCase() }} {{ opp.trade_outcome }}</span>
            <span class="font-mono">${{ opp.trade_amount_usd?.toFixed(2) }}</span>
          </div>
          <div v-if="opp.status === 'trade_proposed'" class="trade-actions">
            <button class="btn btn-success" @click="handleApproveTrade">Approve Trade</button>
            <button class="btn btn-danger" @click="handleRejectTrade">Reject</button>
          </div>
          <div v-if="opp.trade_fill_price" class="trade-fill">
            <span class="text-green">Filled:</span>
            <span class="font-mono">{{ opp.trade_fill_shares?.toFixed(2) }} shares @ ${{ opp.trade_fill_price?.toFixed(4) }}</span>
          </div>
        </div>
      </section>

      <!-- Actions -->
      <section class="detail-section actions-section">
        <button
          v-if="(opp.status === 'discovered' && (opp.simulation_potential || 0) >= 3) || opp.status === 'simulation_running'"
          class="btn btn-primary"
          @click="$router.push(`/opportunity/${opp.id}/simulation`)"
        >
          {{ opp.status === 'simulation_running' ? 'Continue Simulation' : 'Run Simulation' }}
        </button>
        <button
          v-if="opp.status === 'simulation_complete'"
          class="btn btn-primary"
          @click="$router.push(`/opportunity/${opp.id}/trade`)"
        >
          Analyze Trade
        </button>
      </section>
    </div>

    <div v-else class="loading">Loading...</div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { getOpportunity, analyzeReport, approveTrade, rejectTrade } from '../api/agent'

const props = defineProps({ id: String })
const router = useRouter()
const opp = ref(null)

const statusBadgeClass = computed(() => {
  const map = {
    discovered: 'badge-blue', simulation_running: 'badge-yellow',
    simulation_complete: 'badge-purple', trade_proposed: 'badge-yellow',
    trade_executed: 'badge-green', rejected: 'badge-red', failed: 'badge-red',
  }
  return map[opp.value?.status] || 'badge-blue'
})

async function load() {
  const res = await getOpportunity(props.id)
  opp.value = res.data.opportunity
}

async function handleApproveTrade() {
  await approveTrade(props.id)
  await load()
}

async function handleRejectTrade() {
  await rejectTrade(props.id)
  await load()
}

function formatPrice(p) { return p ? parseFloat(p).toFixed(2) : '—' }
function formatNumber(n) {
  if (n >= 1e6) return (n / 1e6).toFixed(1) + 'M'
  if (n >= 1e3) return (n / 1e3).toFixed(1) + 'K'
  return n?.toFixed(0) || '0'
}
function sentimentColor(key) {
  return { bullish: 'fill-green', bearish: 'fill-red', neutral: 'fill-yellow' }[key] || 'fill-blue'
}

onMounted(load)
</script>

<style scoped>
.detail-view { min-height: 100vh; }
.detail-header {
  display: flex; align-items: center; gap: 16px;
  padding: 0 24px; height: 60px; background: #000; color: #fff;
}
.detail-header .logo { font-family: var(--font-mono); font-size: 14px; font-weight: 800; letter-spacing: 2px; color: #fff; margin: 0; }
.detail-header .btn { color: #fff; border-color: #444; }
.detail-header .btn:hover { background: #222; }
.detail-body { max-width: 800px; margin: 0 auto; padding: 24px; }
.detail-section { margin-bottom: 24px; }
.detail-section h2 { font-size: 13px; text-transform: uppercase; letter-spacing: 0.5px; color: var(--text-muted); margin-bottom: 8px; }
.detail-badge-row { display: flex; gap: 6px; margin-bottom: 8px; }
.market-q { font-size: 20px; font-weight: 600; color: var(--text-primary); margin-bottom: 8px; }
.market-desc { font-size: 14px; margin-bottom: 12px; }
.price-row { display: flex; gap: 24px; margin: 16px 0; }
.price-box { display: flex; flex-direction: column; gap: 2px; }
.price-label { font-size: 11px; text-transform: uppercase; color: var(--text-muted); }
.price-val { font-size: 18px; font-weight: 600; }
.meta-row { display: flex; gap: 16px; font-size: 12px; color: var(--text-muted); }
.analysis-text { font-size: 14px; line-height: 1.6; color: var(--text-secondary); }
.sim-rationale { font-size: 13px; color: var(--text-muted); margin-top: 8px; }
.research-text { font-size: 14px; line-height: 1.6; color: var(--text-secondary); white-space: pre-wrap; }
.sentiment-row { display: flex; flex-direction: column; gap: 8px; margin-top: 12px; }
.sentiment-item { display: flex; align-items: center; gap: 8px; }
.sentiment-label { width: 60px; font-size: 12px; text-transform: capitalize; color: var(--text-secondary); }
.sentiment-bar { flex: 1; height: 8px; background: var(--bg-secondary); border-radius: 4px; overflow: hidden; }
.sentiment-fill { height: 100%; border-radius: 4px; transition: width 0.5s ease; }
.fill-green { background: var(--green); }
.fill-red { background: var(--red); }
.fill-yellow { background: var(--yellow); }
.fill-blue { background: var(--accent); }
.sentiment-val { width: 35px; text-align: right; font-size: 12px; }
.trade-summary { display: flex; justify-content: space-between; padding: 8px; background: var(--bg-secondary); border-radius: var(--radius-sm); margin: 8px 0; font-weight: 600; }
.trade-actions { display: flex; gap: 8px; margin-top: 12px; }
.trade-fill { margin-top: 8px; font-size: 13px; }
.actions-section { display: flex; gap: 8px; }
.loading { text-align: center; padding: 60px; color: var(--text-muted); }
</style>
