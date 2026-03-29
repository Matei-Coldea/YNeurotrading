<template>
  <div class="sim-step" :class="{ active: isActive, complete: isComplete }">
    <div class="step-header" @click="toggleExpand">
      <span class="step-indicator">
        <span v-if="isComplete" class="check">✓</span>
        <span v-else-if="isActive" class="spinner"></span>
        <span v-else class="dot"></span>
      </span>
      <span class="step-title">{{ title }}</span>
      <span v-if="subtitle" class="step-subtitle text-muted">{{ subtitle }}</span>
      <span class="expand-arrow" :class="{ open: expanded }">▸</span>
    </div>
    <div v-if="expanded" class="step-content">
      <slot></slot>
    </div>
  </div>
</template>

<script setup>
import { ref, watch, computed } from 'vue'

const props = defineProps({
  title: { type: String, required: true },
  subtitle: { type: String, default: '' },
  status: { type: String, default: 'pending' }, // pending | running | complete
})

const expanded = ref(false)
const isActive = computed(() => props.status === 'running')
const isComplete = computed(() => props.status === 'complete')

// Auto-expand when active
watch(() => props.status, (val) => {
  if (val === 'running') expanded.value = true
})

function toggleExpand() {
  expanded.value = !expanded.value
}
</script>

<style scoped>
.sim-step {
  border: 1px solid var(--border);
  border-radius: var(--radius);
  overflow: hidden;
  transition: border-color 0.3s;
}
.sim-step.active {
  border-color: var(--yellow);
}
.sim-step.complete {
  border-color: var(--green);
}

.step-header {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 12px 16px;
  cursor: pointer;
  background: var(--bg-card);
  transition: background 0.15s;
}
.step-header:hover {
  background: var(--bg-card-hover);
}

.step-indicator {
  width: 20px;
  height: 20px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}
.check {
  color: var(--green);
  font-weight: bold;
  font-size: 14px;
}
.dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: var(--border-light);
}
.spinner {
  width: 14px;
  height: 14px;
  border: 2px solid var(--border-light);
  border-top-color: var(--yellow);
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}
@keyframes spin {
  to { transform: rotate(360deg); }
}

.step-title {
  font-size: 14px;
  font-weight: 600;
  color: var(--text-primary);
  flex: 1;
}
.step-subtitle {
  font-size: 12px;
}
.expand-arrow {
  color: var(--text-muted);
  transition: transform 0.2s;
  font-size: 12px;
}
.expand-arrow.open {
  transform: rotate(90deg);
}

.step-content {
  padding: 12px 16px;
  border-top: 1px solid var(--border);
  background: var(--bg-secondary);
}
</style>
