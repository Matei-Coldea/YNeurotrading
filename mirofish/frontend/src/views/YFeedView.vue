<template>
  <div class="y-page">
    <div class="y-layout">
      <!-- Left Sidebar -->
      <div class="y-sidebar-col">
        <YSidebar :simulationId="simulationId" :isLive="isLive" />
      </div>

      <!-- Center Feed -->
      <div class="y-feed-col">
        <!-- Feed header -->
        <div class="y-feed-header">
          <div class="y-tab active">
            <span>For You</span>
            <div class="y-tab-indicator"></div>
          </div>
          <div class="y-tab">
            <span>Following</span>
          </div>
        </div>

        <!-- Loading state -->
        <div v-if="loading && tweets.length === 0" class="y-loading">
          <div class="y-spinner"></div>
          <span>Loading posts...</span>
        </div>

        <!-- Empty state -->
        <div v-else-if="!loading && tweets.length === 0" class="y-empty">
          <div class="y-empty-icon">Y</div>
          <p>No posts yet</p>
          <p class="y-empty-sub">{{ isLive ? 'Waiting for agents to post...' : 'This simulation has no Twitter posts.' }}</p>
        </div>

        <!-- Tweet list -->
        <template v-else>
          <YTweet
            v-for="tweet in tweets"
            :key="tweet.id"
            :tweet="tweet"
            :isNew="newTweetIds.has(tweet.id)"
          />

          <!-- Infinite scroll sentinel -->
          <div ref="scrollSentinel" class="y-scroll-sentinel">
            <div v-if="loadingMore" class="y-loading-more">
              <div class="y-spinner"></div>
            </div>
            <div v-else-if="!hasMore" class="y-end-of-feed">
              You've reached the end
            </div>
          </div>
        </template>
      </div>

      <!-- Right Panel -->
      <div class="y-right-col">
        <div class="y-right-panel">
          <!-- Search (decorative) -->
          <div class="y-search-box">
            <svg viewBox="0 0 24 24" class="y-search-icon"><path d="M10.25 3.75c-3.59 0-6.5 2.91-6.5 6.5s2.91 6.5 6.5 6.5c1.795 0 3.419-.726 4.596-1.904 1.178-1.177 1.904-2.801 1.904-4.596 0-3.59-2.91-6.5-6.5-6.5zm-8.5 6.5c0-4.694 3.806-8.5 8.5-8.5s8.5 3.806 8.5 8.5c0 1.986-.682 3.815-1.824 5.262l4.781 4.781-1.414 1.414-4.781-4.781c-1.447 1.142-3.276 1.824-5.262 1.824-4.694 0-8.5-3.806-8.5-8.5z"/></svg>
            <input type="text" placeholder="Search" class="y-search-input" disabled />
          </div>

          <!-- Simulation Stats -->
          <div class="y-stats-card">
            <h3 class="y-stats-title">Simulation Info</h3>

            <div class="y-stat-row">
              <span class="y-stat-label">Status</span>
              <span class="y-stat-value" :class="isLive ? 'live' : ''">{{ isLive ? 'Live' : runnerStatus }}</span>
            </div>
            <div class="y-stat-row">
              <span class="y-stat-label">Round</span>
              <span class="y-stat-value">{{ currentRound }} / {{ totalRounds }}</span>
            </div>
            <div class="y-stat-row">
              <span class="y-stat-label">Total Posts</span>
              <span class="y-stat-value">{{ totalPosts }}</span>
            </div>
            <div class="y-stat-row">
              <span class="y-stat-label">Platform</span>
              <span class="y-stat-value">Twitter</span>
            </div>
          </div>

          <!-- Powered by -->
          <div class="y-powered">
            <a :href="dashboardUrl" class="y-powered-link">Powered by MIROFISH</a>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted, nextTick } from 'vue'
import { useRoute } from 'vue-router'
import YSidebar from '../components/YSidebar.vue'
import YTweet from '../components/YTweet.vue'
import { getRunStatus, getRunStatusDetail, getPostsFeed } from '../api/simulation'

const route = useRoute()

const props = defineProps({
  simulationId: { type: String, required: true }
})

// State
const tweets = ref([])
const loading = ref(true)
const loadingMore = ref(false)
const hasMore = ref(true)
const runnerStatus = ref('unknown')
const currentRound = ref(0)
const totalRounds = ref(0)
const totalPosts = ref(0)
const newTweetIds = ref(new Set())
const seenActionIds = ref(new Set())

// Pagination for historical mode
const offset = ref(0)
const PAGE_SIZE = 50

// Polling
let statusPollTimer = null
let detailPollTimer = null

// Scroll sentinel
const scrollSentinel = ref(null)
let observer = null

const isLive = computed(() => runnerStatus.value === 'running' || runnerStatus.value === 'starting')

const dashboardUrl = computed(() => `/simulation/${props.simulationId}/start`)

// --- Data normalization ---

function normalizeAction(action) {
  const args = action.action_args || {}
  const type = action.action_type

  if (type === 'CREATE_POST') {
    return {
      id: `action-${action.agent_id}-${action.round_num}-${action.timestamp}-post`,
      authorName: '',
      handle: action.agent_name || `agent_${action.agent_id}`,
      content: args.content || '',
      quoteContent: null,
      originalAuthor: null,
      isRepost: false,
      repostedBy: null,
      likes: 0,
      reposts: 0,
      comments: 0,
      timestamp: action.timestamp,
      roundNum: action.round_num
    }
  }

  if (type === 'QUOTE_POST') {
    return {
      id: `action-${action.agent_id}-${action.round_num}-${action.timestamp}-quote`,
      authorName: '',
      handle: action.agent_name || `agent_${action.agent_id}`,
      content: args.quote_content || args.content || '',
      quoteContent: args.original_content || args.post_content || '',
      originalAuthor: args.original_author_name || args.post_author_name || 'Unknown',
      isRepost: false,
      repostedBy: null,
      likes: 0,
      reposts: 0,
      comments: 0,
      timestamp: action.timestamp,
      roundNum: action.round_num
    }
  }

  if (type === 'REPOST') {
    return {
      id: `action-${action.agent_id}-${action.round_num}-${action.timestamp}-repost`,
      authorName: '',
      handle: args.original_author_name || 'Unknown',
      content: args.original_content || args.content || '',
      quoteContent: null,
      originalAuthor: null,
      isRepost: true,
      repostedBy: action.agent_name || `agent_${action.agent_id}`,
      likes: 0,
      reposts: 0,
      comments: 0,
      timestamp: action.timestamp,
      roundNum: action.round_num
    }
  }

  return null
}

function normalizePost(post) {
  // user_name can be empty in some DBs; name often has the handle-style value
  const handle = post.user_name || post.name || `user_${post.user_id}`
  const isRepost = !!(post.original_post_id && !post.content && !post.quote_content)
  const originalHandle = post.original_user_name || post.original_name || null

  if (isRepost) {
    // Show the original post's content, attributed to the original author
    return {
      id: `post-${post.post_id}`,
      authorName: post.original_name || '',
      handle: originalHandle || 'unknown',
      content: post.original_content || '',
      quoteContent: null,
      originalAuthor: null,
      isRepost: true,
      repostedBy: handle,
      likes: post.num_likes || 0,
      reposts: post.num_shares || 0,
      comments: 0,
      timestamp: null,
      roundNum: post.created_at
    }
  }

  return {
    id: `post-${post.post_id}`,
    authorName: post.name || '',
    handle: handle,
    content: post.content || '',
    quoteContent: post.quote_content || null,
    originalAuthor: originalHandle,
    isRepost: false,
    repostedBy: null,
    likes: post.num_likes || 0,
    reposts: post.num_shares || 0,
    comments: 0,
    timestamp: null,
    roundNum: post.created_at
  }
}

// --- Live mode ---

async function pollStatus() {
  try {
    const res = await getRunStatus(props.simulationId)
    if (res?.data) {
      const d = res.data
      runnerStatus.value = d.runner_status || 'unknown'
      currentRound.value = d.twitter_current_round || d.current_round || 0
      totalRounds.value = d.total_rounds || 0
      totalPosts.value = d.twitter_actions_count || d.total_actions_count || 0
    }
  } catch (e) {
    // Ignore polling errors
  }
}

async function pollDetail() {
  try {
    const res = await getRunStatusDetail(props.simulationId)
    if (!res?.data?.all_actions) return

    const actions = res?.data?.all_actions
    const postTypes = new Set(['CREATE_POST', 'QUOTE_POST', 'REPOST'])
    const newTweets = []

    for (const action of actions) {
      if (action.platform !== 'twitter') continue
      if (!postTypes.has(action.action_type)) continue

      const normalized = normalizeAction(action)
      if (!normalized) continue
      if (seenActionIds.value.has(normalized.id)) continue

      seenActionIds.value.add(normalized.id)
      newTweets.push(normalized)
    }

    if (newTweets.length > 0) {
      // Mark as new for animation
      const ids = new Set(newTweets.map(t => t.id))
      newTweetIds.value = ids

      // Prepend new tweets (reverse to get newest first)
      tweets.value = [...newTweets.reverse(), ...tweets.value]
      totalPosts.value = tweets.value.length

      // Clear new markers after animation
      setTimeout(() => {
        newTweetIds.value = new Set()
      }, 1000)
    }
  } catch (e) {
    // Ignore polling errors
  }
}

function startLivePolling() {
  statusPollTimer = setInterval(pollStatus, 2000)
  detailPollTimer = setInterval(pollDetail, 3000)
  // Initial fetch
  pollStatus()
  pollDetail()
}

function stopPolling() {
  if (statusPollTimer) clearInterval(statusPollTimer)
  if (detailPollTimer) clearInterval(detailPollTimer)
  statusPollTimer = null
  detailPollTimer = null
}

// --- Historical mode ---

async function loadHistoricalPosts() {
  if (loadingMore.value || !hasMore.value) return
  loadingMore.value = true

  try {
    const res = await getPostsFeed(props.simulationId, 'twitter', PAGE_SIZE, offset.value)
    if (res?.data) {
      const d = res.data
      const newPosts = (d.posts || []).map(normalizePost)

      tweets.value = [...tweets.value, ...newPosts]
      totalPosts.value = d.total || tweets.value.length
      offset.value += newPosts.length
      hasMore.value = newPosts.length >= PAGE_SIZE && tweets.value.length < (d.total || 0)
    }
  } catch (e) {
    console.error('Failed to load posts:', e)
  }

  loadingMore.value = false
}

function setupInfiniteScroll() {
  nextTick(() => {
    if (!scrollSentinel.value) return
    observer = new IntersectionObserver(
      (entries) => {
        if (entries[0].isIntersecting && !isLive.value) {
          loadHistoricalPosts()
        }
      },
      { rootMargin: '200px' }
    )
    observer.observe(scrollSentinel.value)
  })
}

// --- Init ---

async function init() {
  loading.value = true

  try {
    // Detect mode
    const res = await getRunStatus(props.simulationId)
    if (res?.data) {
      const d = res.data
      runnerStatus.value = d.runner_status || 'completed'
      currentRound.value = d.twitter_current_round || d.current_round || 0
      totalRounds.value = d.total_rounds || 0
      totalPosts.value = d.twitter_actions_count || d.total_actions_count || 0
    }
  } catch (e) {
    runnerStatus.value = 'completed'
  }

  if (isLive.value) {
    startLivePolling()
  } else {
    await loadHistoricalPosts()
    setupInfiniteScroll()
  }

  loading.value = false
}

onMounted(init)

onUnmounted(() => {
  stopPolling()
  if (observer) observer.disconnect()
})
</script>

<style scoped>
.y-page {
  background: #000;
  min-height: 100vh;
  color: #E7E9EA;
  font-family: 'Space Grotesk', system-ui, -apple-system, sans-serif;
}

.y-layout {
  display: flex;
  max-width: 1280px;
  margin: 0 auto;
}

.y-sidebar-col {
  width: 275px;
  flex-shrink: 0;
}

.y-feed-col {
  flex: 1;
  max-width: 600px;
  border-left: 1px solid #2F3336;
  border-right: 1px solid #2F3336;
  min-height: 100vh;
}

.y-right-col {
  width: 350px;
  flex-shrink: 0;
}

/* Feed Header */
.y-feed-header {
  display: flex;
  border-bottom: 1px solid #2F3336;
  position: sticky;
  top: 0;
  z-index: 10;
  background: rgba(0, 0, 0, 0.65);
  backdrop-filter: blur(12px);
}

.y-tab {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 16px 0;
  font-size: 15px;
  color: #71767B;
  cursor: pointer;
  position: relative;
  transition: background-color 0.2s;
  font-weight: 500;
}

.y-tab:hover {
  background-color: rgba(231, 233, 234, 0.1);
}

.y-tab.active {
  color: #E7E9EA;
  font-weight: 700;
}

.y-tab-indicator {
  position: absolute;
  bottom: 0;
  width: 56px;
  height: 4px;
  border-radius: 2px;
  background: #1D9BF0;
}

/* Loading */
.y-loading {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 12px;
  padding: 48px;
  color: #71767B;
  font-size: 15px;
}

.y-spinner {
  width: 28px;
  height: 28px;
  border: 3px solid #2F3336;
  border-top-color: #1D9BF0;
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

/* Empty state */
.y-empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 64px 32px;
  text-align: center;
}

.y-empty-icon {
  font-size: 48px;
  font-weight: 900;
  color: #2F3336;
  margin-bottom: 16px;
}

.y-empty p {
  color: #E7E9EA;
  font-size: 20px;
  font-weight: 700;
  margin: 0;
}

.y-empty-sub {
  color: #71767B !important;
  font-size: 15px !important;
  font-weight: 400 !important;
  margin-top: 8px !important;
}

/* Scroll sentinel */
.y-scroll-sentinel {
  padding: 32px;
  display: flex;
  justify-content: center;
}

.y-loading-more {
  display: flex;
  justify-content: center;
}

.y-end-of-feed {
  color: #71767B;
  font-size: 14px;
  text-align: center;
}

/* Right Panel */
.y-right-panel {
  position: sticky;
  top: 0;
  padding: 12px 16px;
}

.y-search-box {
  display: flex;
  align-items: center;
  gap: 12px;
  background: #16181C;
  border-radius: 9999px;
  padding: 10px 16px;
  margin-bottom: 16px;
  border: 1px solid transparent;
}

.y-search-box:focus-within {
  border-color: #1D9BF0;
  background: #000;
}

.y-search-icon {
  width: 18px;
  height: 18px;
  fill: #71767B;
  flex-shrink: 0;
}

.y-search-input {
  background: none;
  border: none;
  outline: none;
  color: #E7E9EA;
  font-size: 15px;
  font-family: 'Space Grotesk', system-ui, sans-serif;
  width: 100%;
}

.y-search-input::placeholder {
  color: #71767B;
}

.y-stats-card {
  background: #16181C;
  border-radius: 16px;
  padding: 16px;
  margin-bottom: 16px;
}

.y-stats-title {
  font-size: 20px;
  font-weight: 700;
  color: #E7E9EA;
  margin: 0 0 16px 0;
}

.y-stat-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 8px 0;
  border-bottom: 1px solid #2F3336;
}

.y-stat-row:last-child {
  border-bottom: none;
}

.y-stat-label {
  color: #71767B;
  font-size: 14px;
}

.y-stat-value {
  color: #E7E9EA;
  font-size: 14px;
  font-weight: 600;
  font-family: 'JetBrains Mono', monospace;
  text-transform: capitalize;
}

.y-stat-value.live {
  color: #00BA7C;
}

.y-powered {
  padding: 12px 0;
}

.y-powered-link {
  color: #71767B;
  font-size: 13px;
  text-decoration: none;
  transition: color 0.2s;
}

.y-powered-link:hover {
  color: #1D9BF0;
}

/* Responsive */
@media (max-width: 1024px) {
  .y-right-col {
    display: none;
  }
}

@media (max-width: 768px) {
  .y-sidebar-col {
    width: 68px;
  }
}
</style>
