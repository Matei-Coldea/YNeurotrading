<template>
  <div class="event-feed">
    <div class="feed-header">
      <h3>Activity</h3>
      <span class="live-dot" :class="{ connected: isConnected }"></span>
    </div>
    <div class="feed-list" ref="feedList">
      <div v-for="event in events" :key="event.id" class="feed-item" :class="eventClass(event)">
        <span class="event-icon">{{ eventIcon(event) }}</span>
        <div class="event-content">
          <span class="event-text">{{ eventText(event) }}</span>
          <span class="event-time text-muted">{{ formatTime(event.created_at) }}</span>
        </div>
      </div>
      <p v-if="!events.length" class="no-events text-muted">Waiting for activity...</p>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted, nextTick, watch } from 'vue'
import { connectEventStream } from '../api/agent'

const events = ref([])
const isConnected = ref(false)
const feedList = ref(null)
let eventSource = null
let lastId = 0

let reconnectTimer = null

function connect() {
  if (eventSource) {
    eventSource.close()
    eventSource = null
  }
  eventSource = connectEventStream(lastId)
  eventSource.onopen = () => { isConnected.value = true }
  eventSource.onerror = () => {
    isConnected.value = false
    // Don't spam reconnect — use a single 10s timer
    if (!reconnectTimer) {
      reconnectTimer = setTimeout(() => {
        reconnectTimer = null
        connect()
      }, 10000)
    }
  }
  eventSource.onmessage = (e) => {
    try {
      const data = JSON.parse(e.data)
      const id = parseInt(e.lastEventId || '0')
      if (id > lastId) lastId = id
      events.value.unshift({ id, ...data })
      if (events.value.length > 50) events.value.pop()
    } catch {}
  }
}

function eventIcon(event) {
  const map = {
    scan_started: '🔍',
    scan_complete: '✅',
    market_found: '📊',
    simulation_approved: '🚀',
    simulation_started: '⚡',
    simulation_progress: '🔄',
    simulation_complete: '🎯',
    ontology_started: '🧬',
    ontology_complete: '🧬',
    graph_started: '🕸',
    graph_complete: '🕸',
    prepare_started: '👥',
    prepare_complete: '👥',
    report_started: '📝',
    report_complete: '📝',
    trade_proposed: '💡',
    trade_approved: '✅',
    trade_executed: '💰',
    trade_rejected: '❌',
    error: '⚠️',
  }
  return map[event.event_type] || '•'
}

function eventText(event) {
  const q = event.payload?.market_question
  const map = {
    scan_started: 'Scanning markets...',
    scan_complete: `Found ${event.payload?.opportunities_found || 0} markets`,
    market_found: q ? `Found: ${q.slice(0, 50)}` : 'Market discovered',
    simulation_approved: 'Simulation approved',
    simulation_started: 'Simulation started',
    simulation_progress: `Round ${event.payload?.round || '?'}/${event.payload?.total_rounds || '?'}`,
    simulation_complete: 'Simulation complete',
    ontology_started: 'Generating ontology...',
    ontology_complete: `Ontology: ${event.payload?.entity_types?.length || 0} entity types`,
    graph_started: 'Building knowledge graph...',
    graph_complete: 'Knowledge graph built',
    prepare_started: 'Generating agent personas...',
    prepare_complete: 'Agents ready',
    report_started: 'Generating report...',
    report_complete: 'Report ready',
    trade_proposed: `Trade proposed: ${event.payload?.trade_side} ${event.payload?.trade_outcome}`,
    trade_approved: 'Trade approved',
    trade_executed: `Traded: ${event.payload?.shares || '?'} shares @ $${event.payload?.avg_price || '?'}`,
    trade_rejected: 'Trade rejected',
    error: event.payload?.message || 'Error occurred',
  }
  return map[event.event_type] || event.event_type
}

function eventClass(event) {
  if (event.event_type === 'error') return 'event-error'
  if (event.event_type.includes('complete') || event.event_type === 'trade_executed') return 'event-success'
  return ''
}

function formatTime(ts) {
  if (!ts) return ''
  const d = new Date(ts)
  return d.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit', second: '2-digit' })
}

onMounted(connect)
onUnmounted(() => {
  if (eventSource) eventSource.close()
  if (reconnectTimer) clearTimeout(reconnectTimer)
})
</script>

<style scoped>
.event-feed {
  padding: 16px;
}
.feed-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 12px;
}
.feed-header h3 {
  font-size: 12px;
  text-transform: uppercase;
  letter-spacing: 1px;
  color: var(--text-muted);
}
.live-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: var(--red);
}
.live-dot.connected {
  background: var(--green);
  animation: pulse 2s infinite;
}
@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.4; }
}
.feed-list {
  display: flex;
  flex-direction: column;
  gap: 4px;
  max-height: 300px;
  overflow-y: auto;
}
.feed-item {
  display: flex;
  gap: 8px;
  padding: 6px 8px;
  border-radius: var(--radius-sm);
  font-size: 12px;
}
.feed-item:hover {
  background: var(--bg-card-hover);
}
.feed-item.event-error {
  background: var(--red-dim);
}
.feed-item.event-success {
  background: var(--green-dim);
}
.event-icon {
  flex-shrink: 0;
  font-size: 12px;
}
.event-content {
  flex: 1;
  display: flex;
  justify-content: space-between;
  gap: 8px;
}
.event-text {
  color: var(--text-secondary);
}
.event-time {
  font-family: var(--font-mono);
  font-size: 11px;
  flex-shrink: 0;
}
.no-events {
  text-align: center;
  padding: 16px 0;
  font-size: 13px;
}
</style>
