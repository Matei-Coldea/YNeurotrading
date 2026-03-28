<template>
  <div class="tweet-card">
    <div v-if="tweet.is_repost" class="repost-header text-muted">
      ↻ {{ tweet.name || tweet.user_name }} reposted
    </div>
    <div class="tweet-body">
      <div class="avatar" :style="{ background: avatarColor }">
        {{ initials }}
      </div>
      <div class="tweet-content">
        <div class="tweet-author">
          <span class="author-name">{{ displayName }}</span>
          <span class="author-handle text-muted">@{{ handle }}</span>
        </div>
        <p class="tweet-text">{{ tweet.content }}</p>
        <div v-if="tweet.original_content" class="quoted-tweet">
          <span class="quoted-author text-muted">@{{ tweet.original_user_name || 'unknown' }}</span>
          <p>{{ tweet.original_content }}</p>
        </div>
        <div class="tweet-engagement">
          <span class="eng-item">💬 {{ tweet.num_comments || 0 }}</span>
          <span class="eng-item">↻ {{ tweet.num_shares || 0 }}</span>
          <span class="eng-item">♥ {{ tweet.num_likes || 0 }}</span>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  tweet: { type: Object, required: true },
})

const COLORS = ['#3b82f6', '#ef4444', '#10b981', '#f59e0b', '#8b5cf6', '#ec4899', '#06b6d4', '#f97316']

const displayName = computed(() => props.tweet.name || props.tweet.user_name || 'Agent')
const handle = computed(() => props.tweet.user_name || props.tweet.name?.toLowerCase().replace(/\s/g, '_') || 'agent')
const initials = computed(() => {
  const name = displayName.value
  return name.split(' ').map(w => w[0]).join('').slice(0, 2).toUpperCase()
})
const avatarColor = computed(() => {
  let hash = 0
  for (const ch of displayName.value) hash = (hash * 31 + ch.charCodeAt(0)) & 0xfffffff
  return COLORS[hash % COLORS.length]
})
</script>

<style scoped>
.tweet-card {
  padding: 10px 12px;
  border-bottom: 1px solid var(--border);
  transition: background 0.1s;
}
.tweet-card:hover {
  background: var(--bg-card-hover);
}
.repost-header {
  font-size: 11px;
  margin-bottom: 4px;
  padding-left: 40px;
}
.tweet-body {
  display: flex;
  gap: 10px;
}
.avatar {
  width: 32px;
  height: 32px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  color: white;
  font-size: 11px;
  font-weight: 700;
  flex-shrink: 0;
}
.tweet-content {
  flex: 1;
  min-width: 0;
}
.tweet-author {
  display: flex;
  align-items: baseline;
  gap: 6px;
  margin-bottom: 2px;
}
.author-name {
  font-size: 13px;
  font-weight: 600;
  color: var(--text-primary);
}
.author-handle {
  font-size: 12px;
}
.tweet-text {
  font-size: 13px;
  line-height: 1.4;
  color: var(--text-secondary);
  white-space: pre-wrap;
  word-break: break-word;
}
.quoted-tweet {
  margin-top: 6px;
  padding: 8px;
  border: 1px solid var(--border);
  border-radius: var(--radius-sm);
  font-size: 12px;
  color: var(--text-muted);
}
.quoted-tweet p {
  margin-top: 2px;
}
.tweet-engagement {
  display: flex;
  gap: 16px;
  margin-top: 6px;
}
.eng-item {
  font-size: 11px;
  color: var(--text-muted);
}
</style>
