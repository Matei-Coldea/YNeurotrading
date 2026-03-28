<template>
  <div class="opp-card card" @click="$emit('select', opp.id)">
    <div class="card-header">
      <span class="badge" :class="statusBadgeClass">{{ statusLabel }}</span>
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
      <div v-if="opp.estimated_edge != null" class="price-item">
        <span class="price-label">Edge</span>
        <span class="price-value font-mono" :class="opp.estimated_edge > 0 ? 'text-green' : 'text-red'">
          {{ opp.estimated_edge > 0 ? '+' : '' }}{{ (opp.estimated_edge * 100).toFixed(1) }}pp
        </span>
      </div>
    </div>

    <p v-if="opp.agent_hypothesis" class="hypothesis">{{ truncate(opp.agent_hypothesis, 120) }}</p>
    <p v-if="opp.simulation_rationale" class="sim-rationale">{{ truncate(opp.simulation_rationale, 100) }}</p>

    <div class="card-actions" @click.stop>
      <button
        v-if="opp.status === 'discovered' && opp.simulation_potential >= 3"
        class="btn btn-primary btn-sm"
        @click="$emit('approve-simulation', opp.id)"
      >
        Run Simulation
      </button>
      <button
        v-if="opp.status === 'trade_proposed'"
        class="btn btn-success btn-sm"
        @click="$emit('approve-trade', opp.id)"
      >
        Approve Trade
      </button>
      <button
        v-if="opp.status === 'trade_proposed'"
        class="btn btn-danger btn-sm"
        @click="$emit('reject-trade', opp.id)"
      >
        Reject
      </button>
      <button
        v-if="opp.status === 'simulation_running' || opp.status === 'simulation_approved'"
        class="btn btn-sm"
        @click="$router.push(`/opportunity/${opp.id}/simulation`)"
      >
        View Simulation
      </button>
    </div>

    <div class="card-meta">
      <span v-if="opp.volume" class="meta-item">Vol: ${{ formatNumber(opp.volume) }}</span>
      <span v-if="opp.tags?.length" class="meta-item">{{ opp.tags.join(', ') }}</span>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  opp: { type: Object, required: true },
})

defineEmits(['select', 'approve-simulation', 'approve-trade', 'reject-trade'])

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
.sim-potential {
  display: flex;
  gap: 3px;
}
.dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: var(--border-light);
}
.dot.filled {
  background: var(--yellow);
}
.market-question {
  font-size: 15px;
  font-weight: 600;
  color: var(--text-primary);
  margin-bottom: 10px;
  line-height: 1.35;
}
.prices {
  display: flex;
  gap: 16px;
  margin-bottom: 10px;
}
.price-item {
  display: flex;
  flex-direction: column;
  gap: 2px;
}
.price-label {
  font-size: 11px;
  text-transform: uppercase;
  color: var(--text-muted);
  letter-spacing: 0.5px;
}
.price-value {
  font-size: 16px;
  font-weight: 600;
}
.hypothesis {
  font-size: 13px;
  color: var(--text-secondary);
  margin-bottom: 6px;
  line-height: 1.4;
}
.sim-rationale {
  font-size: 12px;
  color: var(--text-muted);
  font-style: italic;
  margin-bottom: 10px;
}
.card-actions {
  display: flex;
  gap: 8px;
  margin-bottom: 8px;
}
.card-meta {
  display: flex;
  gap: 12px;
  font-size: 11px;
  color: var(--text-muted);
}
</style>
