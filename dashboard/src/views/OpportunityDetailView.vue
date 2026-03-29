<template>
  <div class="detail-view">
    <header class="detail-header">
      <button class="btn btn-sm" @click="$router.push('/')">← Back</button>
      <h1 class="logo">NEURO-TRADE</h1>
    </header>

    <div v-if="opp" class="detail-body">
      <!-- Status & Action Bar -->
      <div class="action-bar">
        <div class="action-bar-left">
          <span class="badge" :class="statusBadgeClass">{{ statusLabel }}</span>
          <span class="action-hint">{{ actionText }}</span>
        </div>
        <div class="action-bar-right">
          <button v-if="showRunSim" class="btn btn-primary btn-sm"
            @click="$router.push(`/opportunity/${opp.id}/simulation`)">
            {{ opp.status === 'simulation_running' ? 'View Simulation' : 'Run Simulation' }}
          </button>
          <button v-if="opp.status === 'simulation_complete'" class="btn btn-primary btn-sm"
            @click="$router.push(`/opportunity/${opp.id}/trade`)">
            Analyze Trade
          </button>
          <button v-if="opp.mirofish_simulation_id" class="btn btn-sm sim-link-btn"
            @click="$router.push(`/opportunity/${opp.id}/simulation`)">
            Simulation Dashboard
          </button>
        </div>
      </div>

      <!-- Market Overview -->
      <section class="detail-section">
        <h2>Market Overview</h2>
        <div class="card">
          <div class="detail-badge-row">
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

      <!-- Simulation Results -->
      <section v-if="opp.simulation_report_summary" class="detail-section">
        <h2>Simulation Results</h2>
        <div class="card">
          <div class="report-preview">
            <div class="report-rendered" v-html="renderedReport"></div>
          </div>
          <button v-if="opp.mirofish_report_id"
             class="report-full-link"
             @click="openInIframe(`http://localhost:3000/report/${opp.mirofish_report_id}`)">Read full report →</button>
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

      <!-- Trade -->
      <section v-if="opp.outcome_prices?.length >= 2 && !['rejected', 'failed'].includes(opp.status)" class="detail-section">
        <h2>Trade</h2>
        <div class="amount-row">
          <span class="amount-label">Amount</span>
          <div class="amount-presets">
            <button v-for="a in [10, 25, 50, 100, 250]" :key="a"
              class="preset-btn" :class="{ active: tradeAmount === a }"
              @click="tradeAmount = a"
            >${{ a }}</button>
          </div>
          <div class="amount-input-wrap">
            <span class="amount-sign">$</span>
            <input type="number" v-model.number="tradeAmount" min="1" class="amount-input font-mono" />
          </div>
        </div>
        <div class="trade-pair">
          <button class="trade-btn trade-yes" @click.stop="handleManualTrade('Yes')">
            Buy Yes <span class="trade-price font-mono">${{ formatPrice(opp.outcome_prices[0]) }}</span>
          </button>
          <button class="trade-btn trade-no" @click.stop="handleManualTrade('No')">
            Buy No <span class="trade-price font-mono">${{ formatPrice(opp.outcome_prices[1]) }}</span>
          </button>
        </div>
      </section>

      <section v-if="opp.status === 'trade_executed' && opp.trade_fill_price && opp.trade_side !== 'skip' && !opp.trade_reasoning" class="detail-section">
        <h2>Position</h2>
        <div class="card fill-card">
          <span class="fill-label">Filled</span>
          <span class="font-mono">{{ opp.trade_fill_shares?.toFixed(2) }} shares @ ${{ opp.trade_fill_price?.toFixed(4) }}</span>
        </div>
      </section>
    </div>

    <div v-else class="loading">Loading...</div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { marked } from 'marked'
import { getOpportunity, analyzeReport, approveTrade, rejectTrade, manualTrade } from '../api/agent'
import { simIframe } from '../store/simulationIframe'

const props = defineProps({ id: String })
const router = useRouter()
const opp = ref(null)
const tradeAmount = ref(50)

const statusBadgeClass = computed(() => {
  const map = {
    discovered: 'badge-blue', simulation_running: 'badge-yellow',
    simulation_complete: 'badge-purple', trade_proposed: 'badge-yellow',
    trade_executed: 'badge-green', rejected: 'badge-red', failed: 'badge-red',
  }
  return map[opp.value?.status] || 'badge-blue'
})

const statusLabel = computed(() => {
  const map = {
    discovered: 'New', simulation_proposed: 'Sim Proposed',
    simulation_approved: 'Starting Sim', simulation_running: 'Simulating',
    simulation_complete: 'Sim Complete', trade_proposed: 'Trade Ready',
    trade_approved: 'Trading', trade_executed: 'Executed',
    rejected: 'Rejected', failed: 'Failed',
  }
  return map[opp.value?.status] || opp.value?.status
})

const showRunSim = computed(() => {
  const s = opp.value?.status
  return (s === 'discovered' && (opp.value?.simulation_potential || 0) >= 3) ||
         s === 'simulation_running' || s === 'simulation_approved'
})

const renderedReport = computed(() => {
  if (!opp.value?.simulation_report_summary) return ''
  return marked.parse(opp.value.simulation_report_summary)
})

const actionText = computed(() => {
  const map = {
    discovered: 'Ready for analysis',
    simulation_running: 'Simulation in progress',
    simulation_complete: 'Ready for trade analysis',
    trade_proposed: 'Review agent recommendation',
    trade_executed: 'Position open',
    rejected: 'Dismissed',
  }
  return map[opp.value?.status] || ''
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

async function handleManualTrade(outcome) {
  try {
    await manualTrade(props.id, { side: 'buy', outcome, amount_usd: tradeAmount.value })
    await load()
  } catch (e) {
    console.error('Trade failed:', e)
  }
}

function openInIframe(url) {
  simIframe.url = url
  simIframe.visible = true
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
.detail-header .btn { color: #fff; border-color: #444; background: transparent; }
.detail-header .btn:hover { background: #222; }
.detail-body { max-width: 800px; margin: 0 auto; padding: 24px; }
.action-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 16px;
  background: var(--bg-secondary);
  border: 1px solid var(--border);
  border-radius: var(--radius-lg);
  margin-bottom: 24px;
  gap: 12px;
  flex-wrap: wrap;
}
.action-bar-left {
  display: flex;
  align-items: center;
  gap: 10px;
}
.action-hint {
  font-size: 13px;
  color: var(--text-secondary);
}
.action-bar-right {
  display: flex;
  gap: 8px;
  align-items: center;
}
.sim-link-btn {
  color: var(--accent);
  border-color: var(--accent);
}
.sim-link-btn:hover {
  background: var(--accent);
  color: #fff;
}
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
.report-preview {
  position: relative;
  max-height: 200px;
  overflow: hidden;
}
.report-preview::after {
  content: '';
  position: absolute;
  bottom: 0;
  left: 0;
  right: 0;
  height: 60px;
  background: linear-gradient(to bottom, transparent, var(--bg-card));
  pointer-events: none;
}
.report-full-link {
  display: inline-block;
  margin-top: 10px;
  padding: 0;
  border: none;
  background: none;
  font-size: 13px;
  font-weight: 600;
  color: var(--accent);
  cursor: pointer;
  font-family: inherit;
}
.report-full-link:hover { text-decoration: underline; }
.report-rendered { font-size: 14px; line-height: 1.6; color: var(--text-secondary); }
.report-rendered :deep(h1),
.report-rendered :deep(h2),
.report-rendered :deep(h3) { font-size: 15px; font-weight: 600; color: var(--text-primary); margin: 14px 0 6px; }
.report-rendered :deep(h4),
.report-rendered :deep(h5) { font-size: 13px; font-weight: 600; color: var(--text-primary); margin: 10px 0 4px; text-transform: uppercase; letter-spacing: 0.3px; }
.report-rendered :deep(p) { margin: 0 0 10px; }
.report-rendered :deep(ul),
.report-rendered :deep(ol) { margin: 0 0 10px; padding-left: 20px; }
.report-rendered :deep(li) { margin-bottom: 4px; }
.report-rendered :deep(strong) { color: var(--text-primary); }
.report-rendered :deep(blockquote) { border-left: 3px solid var(--border); padding-left: 12px; color: var(--text-muted); margin: 8px 0; }
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

/* Amount selector */
.amount-row {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 12px;
}
.amount-label {
  font-size: 12px;
  text-transform: uppercase;
  color: var(--text-muted);
  letter-spacing: 0.5px;
}
.amount-presets { display: flex; gap: 4px; }
.preset-btn {
  padding: 4px 10px;
  font-size: 12px;
  font-family: var(--font-mono);
  border: 1px solid var(--border);
  border-radius: var(--radius-sm);
  background: var(--bg-primary);
  color: var(--text-secondary);
  cursor: pointer;
}
.preset-btn:hover { background: var(--bg-secondary); }
.preset-btn.active {
  background: var(--text-primary);
  color: var(--bg-primary);
  border-color: var(--text-primary);
}
.amount-input-wrap {
  display: flex;
  align-items: center;
  border: 1px solid var(--border);
  border-radius: var(--radius-sm);
  padding: 0 8px;
  margin-left: auto;
}
.amount-sign { font-size: 13px; color: var(--text-muted); }
.amount-input {
  width: 60px;
  border: none;
  outline: none;
  font-size: 13px;
  padding: 4px 2px;
  background: transparent;
  color: var(--text-primary);
}
.amount-input::-webkit-inner-spin-button { -webkit-appearance: none; }

/* Trade buttons */
.trade-pair { display: flex; gap: 10px; }
.trade-btn {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  padding: 12px 0;
  border-radius: var(--radius);
  font-size: 15px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.15s;
  border: 1.5px solid;
}
.trade-yes {
  background: var(--green-dim);
  border-color: var(--green);
  color: #2e7d32;
}
.trade-yes:hover { background: var(--green); color: #fff; }
.trade-no {
  background: var(--red-dim);
  border-color: var(--red);
  color: #c62828;
}
.trade-no:hover { background: var(--red); color: #fff; }
.trade-price { font-size: 14px; opacity: 0.8; }
.fill-card {
  display: flex; align-items: center; gap: 10px;
}
.fill-label { color: var(--green); font-weight: 600; }
.loading { text-align: center; padding: 60px; color: var(--text-muted); }
</style>
