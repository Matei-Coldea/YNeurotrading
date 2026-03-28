<template>
  <div class="sentiment-chart">
    <h4 class="chart-title">Simulation Sentiment</h4>
    <div class="bars">
      <div v-for="(val, key) in sentiment" :key="key" class="bar-row">
        <span class="bar-label">{{ key }}</span>
        <div class="bar-track">
          <div class="bar-fill" :class="barColor(key)" :style="{ width: (val * 100) + '%' }"></div>
        </div>
        <span class="bar-value font-mono">{{ (val * 100).toFixed(0) }}%</span>
      </div>
    </div>
  </div>
</template>

<script setup>
defineProps({
  sentiment: { type: Object, default: () => ({}) },
})

function barColor(key) {
  return {
    bullish: 'fill-green',
    bearish: 'fill-red',
    neutral: 'fill-yellow',
    positive: 'fill-green',
    negative: 'fill-red',
  }[key.toLowerCase()] || 'fill-blue'
}
</script>

<style scoped>
.chart-title {
  font-size: 12px;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  color: var(--text-muted);
  margin-bottom: 12px;
}
.bars {
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.bar-row {
  display: flex;
  align-items: center;
  gap: 10px;
}
.bar-label {
  width: 70px;
  font-size: 12px;
  text-transform: capitalize;
  color: var(--text-secondary);
}
.bar-track {
  flex: 1;
  height: 10px;
  background: var(--bg-secondary);
  border-radius: 5px;
  overflow: hidden;
}
.bar-fill {
  height: 100%;
  border-radius: 5px;
  transition: width 0.6s ease;
}
.fill-green { background: var(--green); }
.fill-red { background: var(--red); }
.fill-yellow { background: var(--yellow); }
.fill-blue { background: var(--accent); }
.bar-value {
  width: 35px;
  text-align: right;
  font-size: 12px;
  color: var(--text-secondary);
}
</style>
