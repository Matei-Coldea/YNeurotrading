<template>
  <div class="trade-view">
    <header class="detail-header">
      <button class="btn btn-sm" @click="$router.push('/')">← Dashboard</button>
      <h1 class="logo">NEURO-TRADE</h1>
      <span class="badge badge-purple">Trade Analysis</span>
    </header>

    <div v-if="opp" class="trade-body">
      <!-- Market Context -->
      <section class="trade-section">
        <h2>Market</h2>
        <div class="card">
          <h3 class="market-q">{{ opp.market_question }}</h3>
          <div class="price-row">
            <div class="price-box">
              <span class="label">Yes</span>
              <span class="val font-mono">${{ formatPrice(opp.outcome_prices?.[0]) }}</span>
            </div>
            <div class="price-box">
              <span class="label">No</span>
              <span class="val font-mono">${{ formatPrice(opp.outcome_prices?.[1]) }}</span>
            </div>
            <div v-if="opp.probability_estimate" class="price-box">
              <span class="label">Agent Est.</span>
              <span class="val font-mono">{{ (opp.probability_estimate * 100).toFixed(1) }}%</span>
            </div>
            <div v-if="opp.estimated_edge != null" class="price-box">
              <span class="label">Edge</span>
              <span class="val font-mono" :class="opp.estimated_edge > 0 ? 'text-green' : 'text-red'">
                {{ opp.estimated_edge > 0 ? '+' : '' }}{{ (opp.estimated_edge * 100).toFixed(1) }}pp
              </span>
            </div>
          </div>
        </div>
      </section>

      <!-- MiroFish Links -->
      <section class="trade-section links-row">
        <a v-if="opp.mirofish_simulation_id" :href="`http://localhost:3000/y/${opp.mirofish_simulation_id}`" target="_blank" class="btn">
          View Y.com Feed
        </a>
        <a v-if="opp.mirofish_report_id" :href="`http://localhost:3000/report/${opp.mirofish_report_id}`" target="_blank" class="btn">
          View Full Report
        </a>
        <a v-if="opp.mirofish_project_id" :href="`http://localhost:3000/process/${opp.mirofish_project_id}`" target="_blank" class="btn">
          View in MiroFish
        </a>
      </section>

      <!-- Report Summary -->
      <section v-if="opp.simulation_report_summary" class="trade-section">
        <h2>Simulation Report Summary</h2>
        <div class="card">
          <div class="report-preview">
            <div class="report-rendered" v-html="renderedReport"></div>
          </div>
          <a v-if="opp.mirofish_report_id"
             :href="`http://localhost:3000/report/${opp.mirofish_report_id}`"
             target="_blank" class="report-full-link">Read full report →</a>
        </div>
      </section>

      <!-- Sentiment -->
      <section v-if="opp.simulation_sentiment" class="trade-section">
        <h2>Sentiment Analysis</h2>
        <div class="card">
          <div class="sentiment-bars">
            <div v-for="(val, key) in opp.simulation_sentiment" :key="key" class="sent-row">
              <span class="sent-label">{{ key }}</span>
              <div class="sent-track">
                <div class="sent-fill" :class="sentColor(key)" :style="{ width: (val * 100) + '%' }"></div>
              </div>
              <span class="sent-val font-mono">{{ (val * 100).toFixed(0) }}%</span>
            </div>
          </div>
        </div>
      </section>

      <!-- Trade Proposal -->
      <section v-if="opp.trade_reasoning" class="trade-section">
        <h2>Trade Recommendation</h2>
        <div class="card">
          <p class="reasoning">{{ opp.trade_reasoning }}</p>
          <div v-if="opp.trade_side && opp.trade_side !== 'skip'" class="trade-box">
            <span class="trade-dir" :class="opp.trade_side === 'buy' ? 'text-green' : 'text-red'">
              {{ opp.trade_side.toUpperCase() }}
            </span>
            <span>{{ opp.trade_outcome }}</span>
            <span class="font-mono">${{ opp.trade_amount_usd?.toFixed(2) }}</span>
          </div>
          <div v-if="opp.trade_side === 'skip'" class="trade-box skip">
            <span>No trade recommended</span>
          </div>
        </div>
      </section>

      <!-- Actions -->
      <section class="trade-section actions">
        <button v-if="analyzing" class="btn btn-primary" disabled>
          <span class="spinner-sm"></span> Analyzing report...
        </button>
        <button v-else-if="!opp.trade_reasoning" class="btn btn-primary" @click="doAnalyze">
          Generate Trade Analysis
        </button>
        <button v-if="opp.status === 'trade_proposed'" class="btn btn-success" @click="doApproveTrade">
          Approve Trade
        </button>
        <button v-if="opp.status === 'trade_proposed'" class="btn btn-danger" @click="doRejectTrade">
          Reject Trade
        </button>
        <div v-if="opp.trade_fill_price" class="fill-result text-green">
          Filled: {{ opp.trade_fill_shares?.toFixed(2) }} shares @ ${{ opp.trade_fill_price?.toFixed(4) }}
        </div>
      </section>

      <!-- Manual Trade -->
      <section v-if="opp.outcome_prices?.length >= 2 && !['rejected', 'failed'].includes(opp.status)" class="trade-section">
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
          <button class="trade-btn trade-yes" @click="doManualTrade('Yes')">
            Buy Yes <span class="trade-price font-mono">${{ formatPrice(opp.outcome_prices[0]) }}</span>
          </button>
          <button class="trade-btn trade-no" @click="doManualTrade('No')">
            Buy No <span class="trade-price font-mono">${{ formatPrice(opp.outcome_prices[1]) }}</span>
          </button>
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

const props = defineProps({ id: String })
const router = useRouter()
const opp = ref(null)
const analyzing = ref(false)
const tradeAmount = ref(50)

const renderedReport = computed(() => {
  if (!opp.value?.simulation_report_summary) return ''
  return marked.parse(opp.value.simulation_report_summary)
})

async function load() {
  const res = await getOpportunity(props.id)
  opp.value = res.data.opportunity
}

async function doAnalyze() {
  analyzing.value = true
  try {
    await analyzeReport(props.id)
    await load()
  } catch (e) {
    console.error('Analysis failed:', e)
  } finally {
    analyzing.value = false
  }
}

async function doApproveTrade() {
  await approveTrade(props.id)
  await load()
}

async function doRejectTrade() {
  await rejectTrade(props.id)
  await load()
}

async function doManualTrade(outcome) {
  try {
    await manualTrade(props.id, { side: 'buy', outcome, amount_usd: tradeAmount.value })
    await load()
  } catch (e) {
    console.error('Trade failed:', e)
  }
}

function formatPrice(p) { return p ? parseFloat(p).toFixed(2) : '—' }
function sentColor(key) {
  return { bullish: 'fill-green', bearish: 'fill-red', neutral: 'fill-yellow', positive: 'fill-green', negative: 'fill-red' }[key.toLowerCase()] || 'fill-blue'
}

onMounted(load)
</script>

<style scoped>
.trade-view { min-height: 100vh; }
.detail-header {
  display: flex; align-items: center; gap: 16px;
  padding: 0 24px; height: 60px; background: #000; color: #fff;
}
.detail-header .logo { font-family: var(--font-mono); font-size: 14px; font-weight: 800; letter-spacing: 2px; color: #fff; margin: 0; }
.detail-header .btn { color: #fff; border-color: #444; background: transparent; }
.detail-header .btn:hover { background: #222; }

.trade-body { max-width: 700px; margin: 0 auto; padding: 24px; }
.trade-section { margin-bottom: 24px; }
.trade-section h2 { font-size: 12px; text-transform: uppercase; letter-spacing: 0.5px; color: var(--text-muted); margin-bottom: 8px; }
.market-q { font-size: 18px; font-weight: 600; color: var(--text-primary); margin-bottom: 12px; }
.price-row { display: flex; gap: 24px; }
.price-box { display: flex; flex-direction: column; gap: 2px; }
.label { font-size: 11px; text-transform: uppercase; color: var(--text-muted); }
.val { font-size: 18px; font-weight: 600; }

.links-row { display: flex; gap: 8px; flex-wrap: wrap; }
.links-row .btn { text-decoration: none; }

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
  font-size: 13px;
  font-weight: 600;
  color: var(--accent);
  text-decoration: none;
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

.sentiment-bars { display: flex; flex-direction: column; gap: 8px; }
.sent-row { display: flex; align-items: center; gap: 10px; }
.sent-label { width: 70px; font-size: 12px; text-transform: capitalize; color: var(--text-secondary); }
.sent-track { flex: 1; height: 10px; background: var(--bg-secondary); border-radius: 5px; overflow: hidden; }
.sent-fill { height: 100%; border-radius: 5px; transition: width 0.5s; }
.fill-green { background: var(--green); }
.fill-red { background: var(--red); }
.fill-yellow { background: var(--yellow); }
.fill-blue { background: var(--accent); }
.sent-val { width: 35px; text-align: right; font-size: 12px; }

.reasoning { font-size: 14px; line-height: 1.6; color: var(--text-secondary); margin-bottom: 12px; }
.trade-box { display: flex; gap: 12px; padding: 12px; background: var(--bg-secondary); border-radius: var(--radius); font-weight: 600; font-size: 15px; align-items: center; }
.trade-box.skip { color: var(--text-muted); font-weight: 400; }
.trade-dir { font-size: 13px; font-weight: 700; letter-spacing: 1px; }

.actions { display: flex; gap: 8px; align-items: center; flex-wrap: wrap; }
.fill-result { font-size: 14px; font-weight: 600; }

/* Trade section */
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

.spinner-sm {
  display: inline-block; width: 14px; height: 14px;
  border: 2px solid var(--border-light); border-top-color: white;
  border-radius: 50%; animation: spin 0.8s linear infinite;
}
@keyframes spin { to { transform: rotate(360deg); } }
.loading { text-align: center; padding: 60px; color: var(--text-muted); }
</style>
