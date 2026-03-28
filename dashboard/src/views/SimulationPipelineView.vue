<template>
  <div class="redirect-view">
    <header class="detail-header">
      <button class="btn btn-sm" @click="$router.push('/')">← Dashboard</button>
      <h1 class="logo">NEURO-TRADE</h1>
    </header>
    <div class="redirect-body">
      <div v-if="loading" class="loading-state">
        <div class="spinner"></div>
        <p>Generating seed document and simulation prompt...</p>
        <p class="text-muted">The agent is preparing the simulation based on market research.</p>
      </div>
      <div v-else-if="mirofishUrl" class="redirect-state">
        <p>Simulation project created. MiroFish should have opened in a new tab.</p>
        <a :href="mirofishUrl" target="_blank" class="btn btn-primary">Open MiroFish</a>
        <p class="text-muted">Complete the simulation steps in MiroFish, then return here.</p>
        <button class="btn" @click="$router.push('/')">Back to Dashboard</button>
      </div>
      <div v-else-if="error" class="error-state">
        <p class="text-red">{{ error }}</p>
        <button class="btn" @click="$router.push('/')">Back to Dashboard</button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { startSimulation } from '../api/agent'

const props = defineProps({ id: String })

const loading = ref(true)
const mirofishUrl = ref(null)
const error = ref(null)

onMounted(async () => {
  try {
    const res = await startSimulation(props.id)
    mirofishUrl.value = res.data.mirofish_url
    window.open(res.data.mirofish_url, '_blank')
  } catch (e) {
    error.value = e.response?.data?.detail || e.message || 'Failed to start simulation'
  } finally {
    loading.value = false
  }
})
</script>

<style scoped>
.redirect-view { min-height: 100vh; }
.detail-header {
  display: flex; align-items: center; gap: 16px;
  padding: 0 24px; height: 60px; background: #000; color: #fff;
}
.detail-header .logo { font-family: var(--font-mono); font-size: 14px; font-weight: 800; letter-spacing: 2px; color: #fff; margin: 0; }
.detail-header .btn { color: #fff; border-color: #444; }
.detail-header .btn:hover { background: #222; }
.redirect-body {
  display: flex; flex-direction: column; align-items: center; justify-content: center;
  padding: 60px 24px; text-align: center; gap: 16px;
}
.loading-state, .redirect-state, .error-state {
  display: flex; flex-direction: column; align-items: center; gap: 12px;
}
.spinner {
  width: 32px; height: 32px;
  border: 3px solid var(--border-light);
  border-top-color: var(--accent);
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}
@keyframes spin { to { transform: rotate(360deg); } }
</style>
