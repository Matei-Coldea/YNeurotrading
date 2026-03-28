<template>
  <div class="persona-card">
    <div class="persona-avatar" :style="{ background: color }">{{ initials }}</div>
    <div class="persona-info">
      <span class="persona-name">{{ persona.name || persona.user_name }}</span>
      <span class="persona-role text-muted">{{ persona.bio || persona.persona?.slice(0, 60) }}</span>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({ persona: { type: Object, required: true } })

const COLORS = ['#3b82f6', '#ef4444', '#10b981', '#f59e0b', '#8b5cf6', '#ec4899', '#06b6d4', '#f97316']
const name = computed(() => props.persona.name || props.persona.user_name || 'Agent')
const initials = computed(() => name.value.split(' ').map(w => w[0]).join('').slice(0, 2).toUpperCase())
const color = computed(() => {
  let h = 0
  for (const c of name.value) h = (h * 31 + c.charCodeAt(0)) & 0xfffffff
  return COLORS[h % COLORS.length]
})
</script>

<style scoped>
.persona-card {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 6px 8px;
  border-radius: var(--radius-sm);
  background: var(--bg-card);
}
.persona-avatar {
  width: 28px;
  height: 28px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  color: white;
  font-size: 10px;
  font-weight: 700;
  flex-shrink: 0;
}
.persona-info {
  display: flex;
  flex-direction: column;
  min-width: 0;
}
.persona-name {
  font-size: 12px;
  font-weight: 600;
  color: var(--text-primary);
}
.persona-role {
  font-size: 11px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
</style>
