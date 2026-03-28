<template>
  <div class="simulation-view">
    <!-- Header -->
    <header class="sim-header">
      <button class="btn btn-sm" @click="$router.push('/')">← Dashboard</button>
      <h1 class="logo">NEURO-TRADE</h1>
      <span class="badge badge-yellow">Simulation</span>
    </header>

    <div v-if="opp" class="sim-body">
      <!-- Market Context Banner -->
      <div class="market-banner card">
        <h2>{{ opp.market_question }}</h2>
        <div class="banner-stats">
          <span>Market Price: <strong class="font-mono">${{ formatPrice(opp.outcome_prices?.[0]) }}</strong></span>
          <span>Agent Estimate: <strong class="font-mono">{{ opp.probability_estimate ? (opp.probability_estimate * 100).toFixed(1) + '%' : '—' }}</strong></span>
          <span v-if="opp.estimated_edge != null">Edge: <strong class="font-mono" :class="opp.estimated_edge > 0 ? 'text-green' : 'text-red'">
            {{ opp.estimated_edge > 0 ? '+' : '' }}{{ (opp.estimated_edge * 100).toFixed(1) }}pp
          </strong></span>
        </div>
      </div>

      <!-- Pipeline Steps -->
      <div class="pipeline-steps">
        <!-- Step 1: Ontology -->
        <SimulationStep title="Ontology Generation" :subtitle="ontologySubtitle" :status="stepStatus('ontology')">
          <div v-if="ontology.entity_types?.length" class="tag-list">
            <span class="label">Entities:</span>
            <span v-for="t in ontology.entity_types" :key="t" class="tag">{{ t }}</span>
          </div>
          <div v-if="ontology.relation_types?.length" class="tag-list">
            <span class="label">Relations:</span>
            <span v-for="r in ontology.relation_types" :key="r" class="tag tag-dim">{{ r }}</span>
          </div>
        </SimulationStep>

        <!-- Step 2: Knowledge Graph -->
        <SimulationStep title="Knowledge Graph" :subtitle="graphSubtitle" :status="stepStatus('graph')">
          <p v-if="graph.node_count" class="step-stat">{{ graph.node_count }} nodes, {{ graph.edge_count || 0 }} edges</p>
          <div v-if="graph.progress" class="progress-bar">
            <div class="progress-fill" :style="{ width: graph.progress + '%' }"></div>
          </div>
        </SimulationStep>

        <!-- Step 3: Agent Personas -->
        <SimulationStep title="Agent Personas" :subtitle="prepareSubtitle" :status="stepStatus('prepare')">
          <div v-if="personas.length" class="persona-grid">
            <AgentPersonaCard v-for="(p, i) in personas" :key="i" :persona="p" />
          </div>
          <div v-if="prepare.progress" class="progress-bar">
            <div class="progress-fill" :style="{ width: prepare.progress + '%' }"></div>
          </div>
        </SimulationStep>

        <!-- Step 4: Social Simulation (the star) -->
        <SimulationStep title="Social Simulation" :subtitle="simSubtitle" :status="stepStatus('simulation')">
          <div class="sim-feed-section">
            <div class="feed-header-row">
              <span class="font-mono text-muted">Round {{ simulation.round || 0 }} / {{ simulation.total_rounds || '?' }}</span>
              <span class="text-muted">{{ simulation.actions_count || 0 }} actions</span>
              <a
                v-if="opp.mirofish_simulation_id"
                :href="`http://localhost:3000/y/${opp.mirofish_simulation_id}`"
                target="_blank"
                class="btn btn-sm"
              >
                View Full Feed ↗
              </a>
            </div>
            <div class="tweet-feed" ref="tweetFeedEl">
              <TweetCard v-for="tweet in tweets" :key="tweet.post_id || tweet.id" :tweet="tweet" />
              <p v-if="!tweets.length && stepStatus('simulation') === 'running'" class="text-muted feed-empty">
                Waiting for agents to post...
              </p>
            </div>
          </div>
        </SimulationStep>

        <!-- Step 5: Report Generation -->
        <SimulationStep title="Report Generation" :subtitle="reportSubtitle" :status="stepStatus('report')">
          <p v-if="report.sections_done" class="step-stat">
            {{ report.sections_done }} / {{ report.sections_total }} sections
          </p>
          <div v-if="reportSummary" class="report-preview">
            {{ reportSummary }}
          </div>
        </SimulationStep>

        <!-- Step 6: Trade Recommendation -->
        <SimulationStep title="Trade Recommendation" :subtitle="tradeSubtitle" :status="stepStatus('analysis')">
          <div v-if="opp.trade_reasoning" class="trade-rec">
            <p>{{ opp.trade_reasoning }}</p>
            <div v-if="opp.trade_side && opp.trade_side !== 'skip'" class="trade-box">
              <span class="trade-dir" :class="opp.trade_side === 'buy' ? 'text-green' : 'text-red'">
                {{ opp.trade_side.toUpperCase() }}
              </span>
              <span>{{ opp.trade_outcome }}</span>
              <span class="font-mono">${{ opp.trade_amount_usd?.toFixed(2) }}</span>
            </div>
            <div v-if="opp.status === 'trade_proposed'" class="trade-actions">
              <button class="btn btn-success" @click="handleApproveTrade">Approve Trade</button>
              <button class="btn btn-danger" @click="handleRejectTrade">Reject</button>
            </div>
          </div>
        </SimulationStep>
      </div>
    </div>

    <div v-else class="loading">Loading opportunity...</div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import { getOpportunity, connectOpportunityStream, approveTrade, rejectTrade } from '../api/agent'
import { getPostsFeed, getSimulationProfiles } from '../api/mirofish'
import SimulationStep from '../components/SimulationStep.vue'
import TweetCard from '../components/TweetCard.vue'
import AgentPersonaCard from '../components/AgentPersonaCard.vue'

const props = defineProps({ id: String })
const router = useRouter()

const opp = ref(null)
const tweets = ref([])
const personas = ref([])
const reportSummary = ref('')

// Step state tracking
const completedSteps = ref(new Set())
const activeStep = ref(null)
const ontology = ref({})
const graph = ref({})
const prepare = ref({})
const simulation = ref({})
const report = ref({})

let eventSource = null
let tweetPollInterval = null

// Computed subtitles
const ontologySubtitle = computed(() => {
  if (ontology.value.entity_types?.length) return `${ontology.value.entity_types.length} entity types`
  return ''
})
const graphSubtitle = computed(() => graph.value.node_count ? `${graph.value.node_count} nodes` : '')
const prepareSubtitle = computed(() => personas.value.length ? `${personas.value.length} agents` : '')
const simSubtitle = computed(() => {
  if (simulation.value.round) return `Round ${simulation.value.round}/${simulation.value.total_rounds || '?'}`
  return ''
})
const reportSubtitle = computed(() => {
  if (report.value.sections_done) return `${report.value.sections_done}/${report.value.sections_total} sections`
  return ''
})
const tradeSubtitle = computed(() => {
  if (opp.value?.trade_side === 'skip') return 'No trade recommended'
  if (opp.value?.trade_side) return `${opp.value.trade_side.toUpperCase()} ${opp.value.trade_outcome}`
  return ''
})

function stepStatus(step) {
  if (completedSteps.value.has(step)) return 'complete'
  if (activeStep.value === step) return 'running'
  return 'pending'
}

function handleEvent(data) {
  const type = data.event_type
  const payload = data.payload || {}

  // Track step completion
  if (type.endsWith('_complete') || type.endsWith('_started')) {
    const stepName = type.replace('_complete', '').replace('_started', '')
      .replace('simulation_run', 'simulation')
      .replace('simulation_create', 'simulation_create')

    if (type.endsWith('_started')) {
      // Map event types to step names
      const stepMap = {
        ontology_started: 'ontology',
        graph_started: 'graph',
        simulation_create_started: 'simulation_create',
        prepare_started: 'prepare',
        simulation_run_started: 'simulation',
        report_started: 'report',
      }
      activeStep.value = stepMap[type] || stepName
    }
    if (type.endsWith('_complete')) {
      const stepMap = {
        ontology_complete: 'ontology',
        graph_complete: 'graph',
        simulation_create_complete: 'simulation_create',
        prepare_complete: 'prepare',
        simulation_run_complete: 'simulation',
        report_complete: 'report',
      }
      const step = stepMap[type] || stepName
      completedSteps.value.add(step)
      if (activeStep.value === step) activeStep.value = null
    }
  }

  // Step-specific data
  if (type === 'ontology_complete') {
    ontology.value = { entity_types: payload.entity_types, relation_types: payload.relation_types }
  }
  if (type === 'graph_progress' || type === 'graph_complete') {
    graph.value = { ...graph.value, ...payload }
  }
  if (type === 'prepare_progress') {
    prepare.value = { ...prepare.value, ...payload }
  }
  if (type === 'simulation_progress') {
    simulation.value = { ...simulation.value, ...payload }
  }
  if (type === 'report_progress') {
    report.value = { ...report.value, ...payload }
  }

  // Trade recommendation
  if (type === 'trade_proposed') {
    completedSteps.value.add('analysis')
    refreshOpp()
  }

  // Start tweet polling when simulation is running
  if (type === 'simulation_run_started' || type === 'simulation_progress') {
    startTweetPolling()
  }
  if (type === 'simulation_run_complete') {
    stopTweetPolling()
    loadAllTweets()
  }

  // Load profiles when prepare completes
  if (type === 'prepare_complete') {
    loadProfiles()
  }

  // Load report when complete
  if (type === 'report_complete') {
    refreshOpp()
  }
}

async function refreshOpp() {
  try {
    const res = await getOpportunity(props.id)
    opp.value = res.data.opportunity
    if (opp.value.simulation_report_summary) {
      reportSummary.value = opp.value.simulation_report_summary
    }
  } catch {}
}

async function loadProfiles() {
  if (!opp.value?.mirofish_simulation_id) return
  try {
    const res = await getSimulationProfiles(opp.value.mirofish_simulation_id)
    personas.value = res.data?.data || res.data?.profiles || []
  } catch (e) {
    console.warn('Failed to load profiles:', e)
  }
}

async function loadAllTweets() {
  if (!opp.value?.mirofish_simulation_id) return
  try {
    const res = await getPostsFeed(opp.value.mirofish_simulation_id, 30, 0)
    tweets.value = res.data?.data?.posts || []
  } catch (e) {
    console.warn('Failed to load tweets:', e)
  }
}

function startTweetPolling() {
  if (tweetPollInterval) return
  tweetPollInterval = setInterval(async () => {
    if (!opp.value?.mirofish_simulation_id) return
    try {
      const res = await getPostsFeed(opp.value.mirofish_simulation_id, 20, 0)
      const posts = res.data?.data?.posts || []
      // Merge new posts (prepend new ones)
      const existingIds = new Set(tweets.value.map(t => t.post_id))
      const newPosts = posts.filter(p => !existingIds.has(p.post_id))
      if (newPosts.length) {
        tweets.value = [...newPosts, ...tweets.value].slice(0, 50)
      }
    } catch {}
  }, 4000)
}

function stopTweetPolling() {
  if (tweetPollInterval) {
    clearInterval(tweetPollInterval)
    tweetPollInterval = null
  }
}

async function handleApproveTrade() {
  await approveTrade(props.id)
  await refreshOpp()
}

async function handleRejectTrade() {
  await rejectTrade(props.id)
  await refreshOpp()
}

function formatPrice(p) { return p ? parseFloat(p).toFixed(2) : '—' }

onMounted(async () => {
  await refreshOpp()

  // Determine initial state from opportunity status
  const status = opp.value?.status
  if (['simulation_complete', 'trade_proposed', 'trade_approved', 'trade_executed'].includes(status)) {
    // Simulation already done — show all steps as complete
    for (const s of ['ontology', 'graph', 'simulation_create', 'prepare', 'simulation', 'report']) {
      completedSteps.value.add(s)
    }
    if (opp.value?.trade_reasoning) completedSteps.value.add('analysis')
    loadAllTweets()
    loadProfiles()
  }

  // Connect SSE for live updates
  eventSource = connectOpportunityStream(props.id)
  eventSource.onmessage = (e) => {
    try {
      handleEvent(JSON.parse(e.data))
    } catch {}
  }
})

onUnmounted(() => {
  if (eventSource) eventSource.close()
  stopTweetPolling()
})
</script>

<style scoped>
.simulation-view { min-height: 100vh; }
.sim-header {
  display: flex; align-items: center; gap: 16px;
  padding: 12px 24px; border-bottom: 1px solid var(--border); background: var(--bg-secondary);
}
.sim-header .logo { font-size: 14px; font-weight: 700; letter-spacing: 2px; color: var(--accent); margin: 0; }

.sim-body { max-width: 900px; margin: 0 auto; padding: 24px; }

.market-banner {
  margin-bottom: 24px;
  text-align: center;
}
.market-banner h2 {
  font-size: 18px;
  font-weight: 600;
  color: var(--text-primary);
  margin-bottom: 8px;
}
.banner-stats {
  display: flex;
  justify-content: center;
  gap: 24px;
  font-size: 13px;
  color: var(--text-secondary);
}

.pipeline-steps {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

/* Step content styles */
.tag-list {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
  align-items: center;
  margin-bottom: 6px;
}
.tag-list .label {
  font-size: 11px;
  color: var(--text-muted);
  margin-right: 4px;
}
.tag {
  display: inline-block;
  padding: 2px 8px;
  border-radius: 100px;
  font-size: 11px;
  background: var(--purple-dim);
  color: var(--purple);
}
.tag-dim {
  background: rgba(59, 130, 246, 0.1);
  color: var(--accent);
}

.step-stat {
  font-family: var(--font-mono);
  font-size: 13px;
  color: var(--text-secondary);
}

.progress-bar {
  height: 4px;
  background: var(--border);
  border-radius: 2px;
  margin-top: 8px;
  overflow: hidden;
}
.progress-fill {
  height: 100%;
  background: var(--accent);
  border-radius: 2px;
  transition: width 0.5s ease;
}

.persona-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
  gap: 6px;
  margin-bottom: 8px;
}

/* Tweet feed */
.sim-feed-section {}
.feed-header-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 8px;
  font-size: 12px;
}
.tweet-feed {
  max-height: 400px;
  overflow-y: auto;
  border: 1px solid var(--border);
  border-radius: var(--radius);
  background: var(--bg-primary);
}
.feed-empty {
  text-align: center;
  padding: 24px;
  font-size: 13px;
}

/* Report */
.report-preview {
  font-size: 13px;
  line-height: 1.5;
  color: var(--text-secondary);
  max-height: 200px;
  overflow-y: auto;
  white-space: pre-wrap;
}

/* Trade recommendation */
.trade-rec p {
  font-size: 14px;
  line-height: 1.5;
  color: var(--text-secondary);
  margin-bottom: 8px;
}
.trade-box {
  display: flex;
  gap: 12px;
  padding: 10px;
  background: var(--bg-card);
  border-radius: var(--radius-sm);
  font-weight: 600;
  font-size: 15px;
  align-items: center;
  margin-bottom: 12px;
}
.trade-dir {
  font-size: 13px;
  font-weight: 700;
  letter-spacing: 1px;
}
.trade-actions {
  display: flex;
  gap: 8px;
}

.loading {
  text-align: center;
  padding: 60px;
  color: var(--text-muted);
}
</style>
