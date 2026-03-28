<template>
  <div class="y-tweet" :class="{ 'y-tweet-new': isNew }">
    <!-- Repost header -->
    <div v-if="tweet.isRepost" class="y-repost-header">
      <svg viewBox="0 0 24 24" class="y-repost-icon-sm"><path d="M4.5 3.88l4.432 4.14-1.364 1.46L5.5 7.55V16c0 1.1.896 2 2 2H13v2H7.5c-2.209 0-4-1.79-4-4V7.55L1.432 9.48.068 8.02 4.5 3.88zM16.5 6H11V4h5.5c2.209 0 4 1.79 4 4v8.45l2.068-1.93 1.364 1.46-4.432 4.14-4.432-4.14 1.364-1.46 2.068 1.93V8c0-1.1-.896-2-2-2z"/></svg>
      <span>{{ tweet.repostedBy }} reposted</span>
    </div>

    <div class="y-tweet-body">
      <!-- Avatar -->
      <div class="y-avatar" :style="{ backgroundColor: avatarColor }">
        {{ avatarLetter }}
      </div>

      <!-- Content -->
      <div class="y-tweet-content">
        <!-- Header line -->
        <div class="y-tweet-header">
          <span class="y-display-name">{{ displayName }}</span>
          <span class="y-handle">@{{ tweet.handle }}</span>
          <span class="y-separator">·</span>
          <span class="y-time">{{ formattedTime }}</span>
        </div>

        <!-- Tweet text -->
        <div class="y-tweet-text">{{ tweet.content }}</div>

        <!-- Quoted tweet -->
        <div v-if="tweet.quoteContent" class="y-quote-card">
          <div class="y-quote-header">
            <span class="y-quote-author">{{ tweet.originalAuthor || 'Unknown' }}</span>
          </div>
          <div class="y-quote-text">{{ tweet.quoteContent }}</div>
        </div>

        <!-- Engagement row -->
        <div class="y-engagement">
          <button class="y-eng-btn y-eng-reply" title="Reply">
            <svg viewBox="0 0 24 24" class="y-eng-icon"><path d="M1.751 10c0-4.42 3.584-8 8.005-8h4.366c4.49 0 8.129 3.64 8.129 8.13 0 2.25-.893 4.31-2.457 5.83l-5.364 5.21-.965-.935 2.038-1.98H8.75v-2h6.09l-2.57 2.497c1.36-1.325 2.211-3.142 2.211-5.122 0-3.386-2.743-6.13-6.129-6.13H9.756c-3.317 0-6.005 2.69-6.005 6V14h-2v-4z"/></svg>
            <span v-if="tweet.comments > 0" class="y-eng-count">{{ formatCount(tweet.comments) }}</span>
          </button>
          <button class="y-eng-btn y-eng-repost" title="Repost">
            <svg viewBox="0 0 24 24" class="y-eng-icon"><path d="M4.5 3.88l4.432 4.14-1.364 1.46L5.5 7.55V16c0 1.1.896 2 2 2H13v2H7.5c-2.209 0-4-1.79-4-4V7.55L1.432 9.48.068 8.02 4.5 3.88zM16.5 6H11V4h5.5c2.209 0 4 1.79 4 4v8.45l2.068-1.93 1.364 1.46-4.432 4.14-4.432-4.14 1.364-1.46 2.068 1.93V8c0-1.1-.896-2-2-2z"/></svg>
            <span v-if="tweet.reposts > 0" class="y-eng-count">{{ formatCount(tweet.reposts) }}</span>
          </button>
          <button class="y-eng-btn y-eng-like" title="Like">
            <svg viewBox="0 0 24 24" class="y-eng-icon"><path d="M16.697 5.5c-1.222-.06-2.679.51-3.89 2.16l-.805 1.09-.806-1.09C9.984 6.01 8.526 5.44 7.304 5.5c-1.243.07-2.349.78-2.91 1.91-.552 1.12-.633 2.78.479 4.82 1.074 1.97 3.257 4.27 7.129 6.61 3.87-2.34 6.052-4.64 7.126-6.61 1.111-2.04 1.03-3.7.477-4.82-.561-1.13-1.666-1.84-2.908-1.91zm4.187 7.69c-1.351 2.48-4.001 5.12-8.379 7.67l-.503.3-.504-.3c-4.379-2.55-7.029-5.19-8.382-7.67-1.36-2.5-1.41-4.86-.514-6.67.887-1.79 2.647-2.91 4.601-3.01 1.651-.09 3.368.56 4.798 2.01 1.429-1.45 3.146-2.1 4.796-2.01 1.954.1 3.714 1.22 4.601 3.01.896 1.81.846 4.17-.514 6.67z"/></svg>
            <span v-if="tweet.likes > 0" class="y-eng-count">{{ formatCount(tweet.likes) }}</span>
          </button>
          <button class="y-eng-btn y-eng-views" title="Views">
            <svg viewBox="0 0 24 24" class="y-eng-icon"><path d="M8.75 21V3h2v18h-2zM18.75 21V8.5h2V21h-2zM13.75 21v-9h2v9h-2zM3.75 21v-4h2v4h-2z"/></svg>
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  tweet: { type: Object, required: true },
  isNew: { type: Boolean, default: false }
})

const AVATAR_COLORS = [
  '#1D9BF0', '#00BA7C', '#F91880', '#FFD400',
  '#7856FF', '#FF7A00', '#00D4AA', '#F4212E'
]

function hashCode(str) {
  let hash = 0
  for (let i = 0; i < str.length; i++) {
    hash = ((hash << 5) - hash) + str.charCodeAt(i)
    hash |= 0
  }
  return Math.abs(hash)
}

const avatarColor = computed(() => {
  const name = props.tweet.handle || props.tweet.authorName || ''
  return AVATAR_COLORS[hashCode(name) % AVATAR_COLORS.length]
})

const avatarLetter = computed(() => {
  const name = props.tweet.authorName || props.tweet.handle || '?'
  return name.charAt(0).toUpperCase()
})

const displayName = computed(() => {
  if (props.tweet.authorName) return props.tweet.authorName
  if (props.tweet.handle) {
    return props.tweet.handle.replace(/_\d+$/, '').replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase())
  }
  return 'Unknown'
})

const formattedTime = computed(() => {
  const t = props.tweet.timestamp
  if (!t) return `R${props.tweet.roundNum || '?'}`
  const d = new Date(t)
  if (isNaN(d.getTime())) return `Round ${t}`
  const now = new Date()
  const diff = Math.floor((now - d) / 1000)
  if (diff < 60) return `${diff}s`
  if (diff < 3600) return `${Math.floor(diff / 60)}m`
  if (diff < 86400) return `${Math.floor(diff / 3600)}h`
  return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric' })
})

function formatCount(n) {
  if (!n) return ''
  if (n >= 1000000) return (n / 1000000).toFixed(1) + 'M'
  if (n >= 1000) return (n / 1000).toFixed(1) + 'K'
  return String(n)
}
</script>

<style scoped>
.y-tweet {
  padding: 0;
  border-bottom: 1px solid #2F3336;
  transition: background-color 0.2s;
  cursor: pointer;
}

.y-tweet:hover {
  background-color: rgba(255, 255, 255, 0.03);
}

.y-tweet-new {
  animation: fadeIn 0.4s ease;
}

@keyframes fadeIn {
  from { opacity: 0; transform: translateY(-8px); }
  to { opacity: 1; transform: translateY(0); }
}

.y-repost-header {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 4px 0 0 56px;
  color: #71767B;
  font-size: 13px;
  font-weight: 700;
}

.y-repost-icon-sm {
  width: 16px;
  height: 16px;
  fill: #71767B;
}

.y-tweet-body {
  display: flex;
  gap: 12px;
  padding: 12px 16px;
}

.y-avatar {
  width: 40px;
  height: 40px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #fff;
  font-size: 18px;
  font-weight: 700;
  font-family: 'Space Grotesk', system-ui, sans-serif;
  flex-shrink: 0;
}

.y-tweet-content {
  flex: 1;
  min-width: 0;
}

.y-tweet-header {
  display: flex;
  align-items: center;
  gap: 4px;
  flex-wrap: wrap;
}

.y-display-name {
  font-weight: 700;
  font-size: 15px;
  color: #E7E9EA;
  font-family: 'Space Grotesk', system-ui, sans-serif;
}

.y-handle {
  font-size: 15px;
  color: #71767B;
  font-family: 'JetBrains Mono', monospace;
  font-size: 13px;
}

.y-separator {
  color: #71767B;
  font-size: 15px;
  padding: 0 2px;
}

.y-time {
  color: #71767B;
  font-size: 15px;
}

.y-tweet-text {
  margin-top: 4px;
  font-size: 15px;
  color: #E7E9EA;
  line-height: 1.5;
  white-space: pre-wrap;
  word-break: break-word;
  font-family: 'Space Grotesk', system-ui, sans-serif;
}

.y-quote-card {
  margin-top: 12px;
  border: 1px solid #2F3336;
  border-radius: 16px;
  padding: 12px;
  cursor: pointer;
}

.y-quote-card:hover {
  background-color: rgba(255, 255, 255, 0.03);
}

.y-quote-header {
  margin-bottom: 4px;
}

.y-quote-author {
  font-size: 13px;
  font-weight: 700;
  color: #E7E9EA;
}

.y-quote-text {
  font-size: 14px;
  color: #E7E9EA;
  line-height: 1.4;
  display: -webkit-box;
  -webkit-line-clamp: 3;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.y-engagement {
  display: flex;
  justify-content: space-between;
  max-width: 425px;
  margin-top: 12px;
}

.y-eng-btn {
  display: flex;
  align-items: center;
  gap: 4px;
  background: none;
  border: none;
  padding: 4px 8px;
  margin: -4px -8px;
  border-radius: 9999px;
  cursor: pointer;
  transition: all 0.2s;
  color: #71767B;
}

.y-eng-icon {
  width: 18px;
  height: 18px;
  fill: #71767B;
  transition: fill 0.2s;
}

.y-eng-count {
  font-size: 13px;
  font-family: 'Space Grotesk', system-ui, sans-serif;
}

.y-eng-reply:hover {
  color: #1D9BF0;
  background-color: rgba(29, 155, 240, 0.1);
}
.y-eng-reply:hover .y-eng-icon {
  fill: #1D9BF0;
}

.y-eng-repost:hover {
  color: #00BA7C;
  background-color: rgba(0, 186, 124, 0.1);
}
.y-eng-repost:hover .y-eng-icon {
  fill: #00BA7C;
}

.y-eng-like:hover {
  color: #F91880;
  background-color: rgba(249, 24, 128, 0.1);
}
.y-eng-like:hover .y-eng-icon {
  fill: #F91880;
}

.y-eng-views:hover {
  color: #1D9BF0;
  background-color: rgba(29, 155, 240, 0.1);
}
.y-eng-views:hover .y-eng-icon {
  fill: #1D9BF0;
}
</style>
