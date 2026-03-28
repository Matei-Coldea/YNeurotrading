<template>
  <div class="pipeline-funnel">
    <div class="funnel-header">
      <h3>Pipeline</h3>
    </div>
    <div class="funnel-stages">
      <div
        v-for="stage in stages"
        :key="stage.status"
        class="funnel-stage"
        :class="{ active: activeFilter === stage.status }"
        @click="$emit('filter', stage.status === activeFilter ? null : stage.status)"
      >
        <span class="stage-dot" :style="{ background: stage.color }"></span>
        <span class="stage-label">{{ stage.label }}</span>
        <span class="stage-count">{{ stage.count }}</span>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  opportunities: { type: Array, default: () => [] },
  activeFilter: { type: String, default: null },
})

defineEmits(['filter'])

const stages = computed(() => {
  const counts = {}
  for (const opp of props.opportunities) {
    counts[opp.status] = (counts[opp.status] || 0) + 1
  }
  return [
    { status: 'discovered', label: 'Discovered', color: '#3b82f6', count: counts.discovered || 0 },
    { status: 'simulation_running', label: 'Simulating', color: '#f59e0b', count: (counts.simulation_running || 0) + (counts.simulation_approved || 0) },
    { status: 'simulation_complete', label: 'Analyzed', color: '#8b5cf6', count: counts.simulation_complete || 0 },
    { status: 'trade_proposed', label: 'Trade Proposed', color: '#f97316', count: counts.trade_proposed || 0 },
    { status: 'trade_executed', label: 'Executed', color: '#10b981', count: (counts.trade_executed || 0) + (counts.trade_approved || 0) },
    { status: 'rejected', label: 'Rejected', color: '#6b7280', count: counts.rejected || 0 },
  ]
})
</script>

<style scoped>
.pipeline-funnel {
  padding: 16px;
}
.funnel-header h3 {
  font-size: 12px;
  text-transform: uppercase;
  letter-spacing: 1px;
  color: var(--text-muted);
  margin-bottom: 16px;
}
.funnel-stages {
  display: flex;
  flex-direction: column;
  gap: 4px;
}
.funnel-stage {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 8px 12px;
  border-radius: var(--radius);
  cursor: pointer;
  transition: background 0.15s;
}
.funnel-stage:hover {
  background: var(--bg-card-hover);
}
.funnel-stage.active {
  background: var(--bg-card);
  border: 1px solid var(--border-light);
}
.stage-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  flex-shrink: 0;
}
.stage-label {
  flex: 1;
  font-size: 13px;
  color: var(--text-secondary);
}
.stage-count {
  font-family: var(--font-mono);
  font-size: 13px;
  color: var(--text-primary);
  font-weight: 600;
}
</style>
