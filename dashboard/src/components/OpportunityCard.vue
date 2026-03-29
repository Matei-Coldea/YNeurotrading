<template>
  <div class="opp-card card" @click="$emit('select', opp.id)">
    <div class="card-header">
      <div class="header-badges">
        <span class="badge" :class="statusBadgeClass">{{ statusLabel }}</span>
        <span v-if="opp.simulation_category" class="badge sim-category-badge" :class="simCategoryClass" :title="simCategoryTooltip">
          {{ simCategoryLabel }}
        </span>
      </div>
      <span v-if="opp.simulation_potential" class="sim-potential" :title="`Simulation potential: ${opp.simulation_potential}/5`">
        <span v-for="i in 5" :key="i" class="dot" :class="{ filled: i <= opp.simulation_potential }"></span>
      </span>
    </div>

    <h3 class="market-question">{{ opp.market_question }}</h3>

    <div class="prices">
      <div class="price-item">
        <span class="price-label">Yes</span>
        <span class="price-value font-mono">${{ formatPrice(opp.outcome_prices?.[0]) }}</span>
      </div>
      <div class="price-item">
        <span class="price-label">No</span>
        <span class="price-value font-mono">${{ formatPrice(opp.outcome_prices?.[1]) }}</span>
      </div>
      <div v-if="opp.estimated_edge != null && opp.estimated_edge !== 0" class="price-item">
        <span class="price-label">Edge</span>
        <span class="price-value font-mono" :class="opp.estimated_edge > 0 ? 'text-green' : 'text-red'">
          {{ opp.estimated_edge > 0 ? '+' : '' }}{{ (opp.estimated_edge * 100).toFixed(1) }}pp
        </span>
      </div>
    </div>

    <p v-if="opp.agent_hypothesis" class="hypothesis">{{ truncate(opp.agent_hypothesis, 120) }}</p>
    <p v-if="opp.simulation_rationale" class="sim-rationale">{{ truncate(opp.simulation_rationale, 100) }}</p>

    <!-- Workflow actions -->
    <div class="card-actions" @click.stop>
      <button
        v-if="(opp.status === 'discovered' && opp.simulation_potential >= 3) || opp.status === 'simulation_running'"
        class="btn btn-primary btn-sm"
        @click="$emit('start-simulation', opp.id)"
      >
        {{ opp.status === 'simulation_running' ? 'View Simulation' : 'Run Simulation' }}
      </button>
      <button
        v-if="opp.status === 'simulation_complete'"
        class="btn btn-primary btn-sm"
        @click="$emit('analyze-report', opp.id)"
      >
        Analyze Trade
      </button>
      <template v-if="opp.status === 'trade_proposed'">
        <button v-if="opp.trade_side !== 'skip'" class="btn btn-sm btn-outline" @click="$emit('approve-trade', opp.id)">
          Approve Agent Rec.
        </button>
        <span v-else class="rec-label">Agent: No trade</span>
        <button class="btn btn-sm btn-outline-dim" @click="$emit('reject-trade', opp.id)">Dismiss</button>
      </template>
    </div>

    <!-- Executed fill -->
    <div v-if="opp.status === 'trade_executed' && opp.trade_fill_price && opp.trade_side !== 'skip'" class="fill-row" @click.stop>
      <span class="fill-label">Filled</span>
      <span class="fill-detail font-mono">{{ opp.trade_fill_shares?.toFixed(1) }} shares @ ${{ opp.trade_fill_price?.toFixed(3) }}</span>
    </div>

    <!-- Trade buttons — only show when no trade executed/rejected -->
    <div v-if="opp.outcome_prices?.length >= 2 && !['rejected', 'failed'].includes(opp.status)" class="trade-section" @click.stop>
      <div class="amount-row">
        <span class="amount-label">Amount</span>
        <div class="amount-presets">
          <button v-for="a in [10, 25, 50, 100]" :key="a"
            class="preset-btn" :class="{ active: tradeAmount === a }"
            @click="tradeAmount = a"
          >${{ a }}</button>
        </div>
        <div class="amount-input-wrap">
          <span class="amount-sign">$</span>
          <input type="number" v-model.number="tradeAmount" min="1" class="amount-input font-mono" @click.stop />
        </div>
      </div>
      <div class="trade-pair">
        <button class="trade-btn trade-yes" @click="$emit('manual-trade', { id: opp.id, outcome: 'Yes', amount: tradeAmount })">
          Buy Yes <span class="trade-price font-mono">${{ parseFloat(opp.outcome_prices[0]).toFixed(2) }}</span>
        </button>
        <button class="trade-btn trade-no" @click="$emit('manual-trade', { id: opp.id, outcome: 'No', amount: tradeAmount })">
          Buy No <span class="trade-price font-mono">${{ parseFloat(opp.outcome_prices[1]).toFixed(2) }}</span>
        </button>
      </div>
    </div>

    <div class="card-meta">
      <span v-if="opp.volume" class="meta-item">Vol: ${{ formatNumber(opp.volume) }}</span>
      <span v-if="opp.tags?.length" class="meta-item">{{ opp.tags.join(', ') }}</span>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'

const props = defineProps({
  opp: { type: Object, required: true },
})

const tradeAmount = ref(50)

defineEmits(['select', 'start-simulation', 'analyze-report', 'approve-trade', 'reject-trade', 'manual-trade'])

const simCategoryLabel = computed(() => {
  if (props.opp.simulation_category === 'direct') return 'Opinion → Outcome'
  return ''
})

const simCategoryClass = computed(() => {
  if (props.opp.simulation_category === 'direct') return 'badge-cyan'
  return ''
})

const simCategoryTooltip = computed(() => {
  if (props.opp.simulation_category === 'direct')
    return 'Public opinion determines the outcome — simulation directly predicts the result'
  return ''
})

const statusBadgeClass = computed(() => {
  const map = {
    discovered: 'badge-blue',
    simulation_proposed: 'badge-blue',
    simulation_approved: 'badge-yellow',
    simulation_running: 'badge-yellow',
    simulation_complete: 'badge-purple',
    trade_proposed: 'badge-yellow',
    trade_approved: 'badge-green',
    trade_executed: 'badge-green',
    rejected: 'badge-red',
    failed: 'badge-red',
  }
  return map[props.opp.status] || 'badge-blue'
})

const statusLabel = computed(() => {
  const map = {
    discovered: 'New',
    simulation_proposed: 'Sim Proposed',
    simulation_approved: 'Sim Approved',
    simulation_running: 'Simulating',
    simulation_complete: 'Analyzed',
    trade_proposed: 'Trade Ready',
    trade_approved: 'Trading',
    trade_executed: 'Executed',
    rejected: 'Rejected',
    failed: 'Failed',
  }
  return map[props.opp.status] || props.opp.status
})

function formatPrice(p) {
  if (!p) return '—'
  return parseFloat(p).toFixed(2)
}

function formatNumber(n) {
  if (n >= 1e6) return (n / 1e6).toFixed(1) + 'M'
  if (n >= 1e3) return (n / 1e3).toFixed(1) + 'K'
  return n.toFixed(0)
}

function truncate(s, len) {
  if (!s) return ''
  return s.length > len ? s.slice(0, len) + '...' : s
}
</script>

<style scoped>
.opp-card {
  cursor: pointer;
  transition: border-color 0.15s, transform 0.1s;
}
.opp-card:hover {
  transform: translateY(-1px);
}
.card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 8px;
}
.header-badges {
  display: flex;
  align-items: center;
  gap: 6px;
}
.sim-category-badge {
  font-size: 10px;
  font-weight: 600;
  letter-spacing: 0.3px;
  cursor: help;
}
.badge-cyan {
  background: rgba(0, 188, 212, 0.12);
  color: #00acc1;
  border: 1px solid rgba(0, 188, 212, 0.25);
}
.sim-potential { display: flex; gap: 3px; }
.dot { width: 6px; height: 6px; border-radius: 50%; background: var(--border-light); }
.dot.filled { background: var(--yellow); }
.market-question {
  font-size: 15px;
  font-weight: 600;
  color: var(--text-primary);
  margin-bottom: 10px;
  line-height: 1.35;
}
.prices { display: flex; gap: 16px; margin-bottom: 10px; }
.price-item { display: flex; flex-direction: column; gap: 2px; }
.price-label { font-size: 11px; text-transform: uppercase; color: var(--text-muted); letter-spacing: 0.5px; }
.price-value { font-size: 16px; font-weight: 600; }
.hypothesis { font-size: 13px; color: var(--text-secondary); margin-bottom: 6px; line-height: 1.4; }
.sim-rationale { font-size: 12px; color: var(--text-muted); font-style: italic; margin-bottom: 10px; }

/* Workflow actions row */
.card-actions {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 10px;
  flex-wrap: wrap;
}
.btn-outline {
  background: none;
  border: 1px solid var(--border);
  color: var(--text-secondary);
  font-size: 12px;
}
.btn-outline:hover { background: var(--bg-secondary); }
.btn-outline-dim {
  background: none;
  border: 1px solid var(--border-light);
  color: var(--text-muted);
  font-size: 12px;
}
.btn-outline-dim:hover { background: var(--bg-secondary); }
.rec-label {
  font-size: 12px;
  color: var(--text-muted);
  font-style: italic;
}

/* Trade section */
.trade-section { margin-bottom: 10px; }
.amount-row {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 8px;
}
.amount-label {
  font-size: 11px;
  text-transform: uppercase;
  color: var(--text-muted);
  letter-spacing: 0.5px;
}
.amount-presets { display: flex; gap: 4px; }
.preset-btn {
  padding: 3px 8px;
  font-size: 11px;
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
  padding: 0 6px;
  margin-left: auto;
}
.amount-sign { font-size: 12px; color: var(--text-muted); }
.amount-input {
  width: 50px;
  border: none;
  outline: none;
  font-size: 12px;
  padding: 3px 2px;
  background: transparent;
  color: var(--text-primary);
}
.amount-input::-webkit-inner-spin-button { -webkit-appearance: none; }

/* Trade Yes/No pair */
.trade-pair {
  display: flex;
  gap: 8px;
  margin-bottom: 10px;
}
.trade-btn {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  padding: 8px 0;
  border-radius: var(--radius);
  font-size: 13px;
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
.trade-price { font-size: 12px; opacity: 0.8; }

/* Fill row */
.fill-row {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 6px 10px;
  background: var(--green-dim);
  border-radius: var(--radius-sm);
  margin-bottom: 10px;
  font-size: 12px;
}
.fill-label { color: var(--green); font-weight: 600; }
.fill-detail { color: var(--text-secondary); }

.card-meta { display: flex; gap: 12px; font-size: 11px; color: var(--text-muted); }
</style>
