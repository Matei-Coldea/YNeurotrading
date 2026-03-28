<template>
  <div class="edge-bar">
    <div class="bar-labels">
      <span class="text-muted">Market: {{ (marketPrice * 100).toFixed(1) }}%</span>
      <span class="text-muted">Agent: {{ (agentEstimate * 100).toFixed(1) }}%</span>
    </div>
    <div class="bar-track">
      <div class="bar-market" :style="{ width: (marketPrice * 100) + '%' }"></div>
      <div class="bar-agent" :style="{ left: (agentEstimate * 100) + '%' }"></div>
      <div
        v-if="edge !== 0"
        class="bar-edge"
        :class="edge > 0 ? 'edge-positive' : 'edge-negative'"
        :style="edgeStyle"
      ></div>
    </div>
    <div class="edge-label font-mono" :class="edge > 0 ? 'text-green' : 'text-red'">
      {{ edge > 0 ? '+' : '' }}{{ (edge * 100).toFixed(1) }}pp edge
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  marketPrice: { type: Number, default: 0.5 },
  agentEstimate: { type: Number, default: 0.5 },
})

const edge = computed(() => props.agentEstimate - props.marketPrice)

const edgeStyle = computed(() => {
  const left = Math.min(props.marketPrice, props.agentEstimate) * 100
  const width = Math.abs(edge.value) * 100
  return { left: left + '%', width: width + '%' }
})
</script>

<style scoped>
.edge-bar {
  padding: 8px 0;
}
.bar-labels {
  display: flex;
  justify-content: space-between;
  font-size: 11px;
  margin-bottom: 4px;
}
.bar-track {
  position: relative;
  height: 8px;
  background: var(--bg-secondary);
  border-radius: 4px;
  overflow: visible;
}
.bar-market {
  position: absolute;
  top: 0;
  left: 0;
  height: 100%;
  background: var(--border-light);
  border-radius: 4px;
}
.bar-agent {
  position: absolute;
  top: -2px;
  width: 3px;
  height: 12px;
  background: var(--accent);
  border-radius: 2px;
  transform: translateX(-1px);
}
.bar-edge {
  position: absolute;
  top: 2px;
  height: 4px;
  border-radius: 2px;
}
.edge-positive {
  background: rgba(16, 185, 129, 0.4);
}
.edge-negative {
  background: rgba(239, 68, 68, 0.4);
}
.edge-label {
  text-align: center;
  font-size: 12px;
  margin-top: 4px;
}
</style>
