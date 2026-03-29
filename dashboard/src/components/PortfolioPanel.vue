<template>
  <div class="portfolio-panel">
    <div class="panel-header">
      <h3>Portfolio</h3>
      <button class="btn btn-sm" @click="refresh">Refresh</button>
    </div>

    <div class="balance-row">
      <span class="balance-label">Cash</span>
      <span class="balance-value font-mono">${{ portfolio.cash_balance?.toFixed(2) || '—' }}</span>
    </div>

    <div v-if="portfolio.pnl_summary" class="pnl-row">
      <span class="pnl-label">P&L</span>
      <span
        class="pnl-value font-mono"
        :class="(portfolio.pnl_summary.cash_pnl || 0) >= 0 ? 'text-green' : 'text-red'"
      >
        {{ (portfolio.pnl_summary.cash_pnl || 0) >= 0 ? '+' : '' }}${{ (portfolio.pnl_summary.cash_pnl || 0).toFixed(2) }}
      </span>
    </div>

    <div class="positions-header">
      <h4>Positions ({{ portfolio.num_positions || 0 }})</h4>
    </div>

    <div v-if="portfolio.positions?.length" class="positions-list">
      <div v-for="pos in portfolio.positions" :key="pos.token_id" class="position-item">
        <div class="pos-info">
          <span class="pos-question">{{ truncate(pos.market_question, 40) }}</span>
          <span class="pos-outcome badge badge-blue">{{ pos.outcome }}</span>
        </div>
        <div class="pos-numbers">
          <span class="font-mono">{{ pos.shares?.toFixed(1) }} shares</span>
          <span class="text-muted font-mono">@ ${{ pos.avg_cost?.toFixed(3) }}</span>
          <button class="btn btn-danger btn-xs" @click="handleSell(pos.token_id)">Sell</button>
        </div>
      </div>
    </div>
    <p v-else class="no-positions text-muted">No open positions</p>

    <!-- Recent trade decisions -->
    <div class="decisions-header">
      <h4>Recent Decisions</h4>
    </div>
    <div v-if="decisions.length" class="decisions-list">
      <div v-for="d in decisions" :key="d.id" class="decision-item">
        <span class="dec-question">{{ truncate(d.market_question, 35) }}</span>
        <div class="dec-detail">
          <span v-if="d.trade_side === 'skip'" class="badge badge-yellow">Skip</span>
          <span v-else-if="d.trade_side === 'buy'" class="badge badge-green">Buy {{ d.trade_outcome }}</span>
          <span v-else-if="d.trade_side === 'sell'" class="badge badge-red">Sell {{ d.trade_outcome }}</span>
          <span v-if="d.trade_fill_price" class="font-mono dec-fill">
            {{ d.trade_fill_shares?.toFixed(1) }}sh @ ${{ d.trade_fill_price?.toFixed(3) }}
          </span>
        </div>
      </div>
    </div>
    <p v-else class="no-positions text-muted">No trade decisions yet</p>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { getPortfolio, getOpportunities, sellPosition } from '../api/agent'

const portfolio = ref({})
const decisions = ref([])

async function refresh() {
  try {
    const res = await getPortfolio()
    portfolio.value = res.data
  } catch (e) {
    console.error('Failed to load portfolio:', e)
  }
  try {
    const res = await getOpportunities()
    const opps = res.data.opportunities || []
    decisions.value = opps.filter(o =>
      ['trade_proposed', 'trade_approved', 'trade_executed', 'rejected'].includes(o.status)
    )
  } catch {}
}

async function handleSell(tokenId) {
  try {
    await sellPosition(tokenId)
    await refresh()
  } catch (e) {
    console.error('Sell failed:', e)
  }
}

function truncate(s, len) {
  if (!s) return ''
  return s.length > len ? s.slice(0, len) + '...' : s
}

onMounted(refresh)

defineExpose({ refresh })
</script>

<style scoped>
.portfolio-panel {
  padding: 16px;
}
.panel-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 16px;
}
.panel-header h3 {
  font-size: 12px;
  text-transform: uppercase;
  letter-spacing: 1px;
  color: var(--text-muted);
}
.balance-row, .pnl-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 8px 0;
}
.balance-label, .pnl-label {
  font-size: 13px;
  color: var(--text-secondary);
}
.balance-value {
  font-size: 20px;
  font-weight: 700;
  color: var(--text-primary);
}
.pnl-value {
  font-size: 15px;
  font-weight: 600;
}
.positions-header {
  margin-top: 16px;
  padding-top: 12px;
  border-top: 1px solid var(--border);
}
.positions-header h4 {
  font-size: 12px;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  color: var(--text-muted);
  margin-bottom: 8px;
}
.positions-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.position-item {
  padding: 8px;
  background: var(--bg-secondary);
  border-radius: var(--radius-sm);
}
.pos-info {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-bottom: 4px;
}
.pos-question {
  font-size: 12px;
  color: var(--text-primary);
  flex: 1;
}
.pos-numbers {
  display: flex;
  gap: 8px;
  font-size: 12px;
  align-items: center;
}
.btn-xs {
  font-size: 10px;
  padding: 2px 6px;
  border-radius: 3px;
}
.no-positions {
  font-size: 13px;
  text-align: center;
  padding: 16px 0;
}
.decisions-header {
  margin-top: 16px;
  padding-top: 12px;
  border-top: 1px solid var(--border);
}
.decisions-header h4 {
  font-size: 12px;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  color: var(--text-muted);
  margin-bottom: 8px;
}
.decisions-list { display: flex; flex-direction: column; gap: 6px; }
.decision-item {
  padding: 6px 8px;
  background: var(--bg-secondary);
  border-radius: var(--radius-sm);
}
.dec-question { font-size: 11px; color: var(--text-primary); display: block; margin-bottom: 3px; }
.dec-detail { display: flex; align-items: center; gap: 6px; }
.dec-fill { font-size: 11px; color: var(--text-muted); }
</style>
