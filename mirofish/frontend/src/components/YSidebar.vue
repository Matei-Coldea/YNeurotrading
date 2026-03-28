<template>
  <div class="y-sidebar">
    <!-- Logo -->
    <div class="y-logo">Y</div>

    <!-- Nav items (decorative) -->
    <nav class="y-nav">
      <a class="y-nav-item active" href="#">
        <svg viewBox="0 0 24 24" class="y-nav-icon"><path d="M21.591 7.146L12.52 1.157c-.316-.21-.724-.21-1.04 0l-9.071 5.99c-.26.173-.409.456-.409.757v13.183c0 .502.418.913.929.913h6.638c.511 0 .929-.41.929-.913v-7.075h3.008v7.075c0 .502.418.913.929.913h6.638c.511 0 .929-.41.929-.913V7.903c0-.301-.158-.584-.409-.757z"/></svg>
        <span class="y-nav-label">Home</span>
      </a>
      <a class="y-nav-item" href="#">
        <svg viewBox="0 0 24 24" class="y-nav-icon"><path d="M10.25 3.75c-3.59 0-6.5 2.91-6.5 6.5s2.91 6.5 6.5 6.5c1.795 0 3.419-.726 4.596-1.904 1.178-1.177 1.904-2.801 1.904-4.596 0-3.59-2.91-6.5-6.5-6.5zm-8.5 6.5c0-4.694 3.806-8.5 8.5-8.5s8.5 3.806 8.5 8.5c0 1.986-.682 3.815-1.824 5.262l4.781 4.781-1.414 1.414-4.781-4.781c-1.447 1.142-3.276 1.824-5.262 1.824-4.694 0-8.5-3.806-8.5-8.5z"/></svg>
        <span class="y-nav-label">Explore</span>
      </a>
      <a class="y-nav-item" href="#">
        <svg viewBox="0 0 24 24" class="y-nav-icon"><path d="M19.993 9.042C19.48 5.017 16.054 2 11.996 2s-7.49 3.021-7.999 7.051L2.866 18H7.1c.463 2.282 2.481 4 4.9 4s4.437-1.718 4.9-4h4.236l-1.143-8.958zM12 20c-1.306 0-2.417-.835-2.829-2h5.658c-.412 1.165-1.523 2-2.829 2zm-6.866-4l.847-6.698C6.364 6.272 8.941 4 11.996 4s5.627 2.268 6.013 5.295L18.858 16H5.134z"/></svg>
        <span class="y-nav-label">Notifications</span>
      </a>
      <a class="y-nav-item" href="#">
        <svg viewBox="0 0 24 24" class="y-nav-icon"><path d="M1.998 5.5c0-1.381 1.119-2.5 2.5-2.5h15c1.381 0 2.5 1.119 2.5 2.5v13c0 1.381-1.119 2.5-2.5 2.5h-15c-1.381 0-2.5-1.119-2.5-2.5v-13zm2.5-.5c-.276 0-.5.224-.5.5v2.764l8 3.638 8-3.636V5.5c0-.276-.224-.5-.5-.5h-15zm15.5 5.463l-8 3.636-8-3.638V18.5c0 .276.224.5.5.5h15c.276 0 .5-.224.5-.5v-8.037z"/></svg>
        <span class="y-nav-label">Messages</span>
      </a>
      <a class="y-nav-item" href="#">
        <svg viewBox="0 0 24 24" class="y-nav-icon"><path d="M5.651 19h12.698c-.337-1.8-1.023-3.21-1.945-4.19C15.318 13.65 13.838 13 12 13s-3.317.65-4.404 1.81c-.922.98-1.608 2.39-1.945 4.19zm.486-5.56C7.627 11.85 9.648 11 12 11s4.373.85 5.863 2.44c1.477 1.58 2.366 3.8 2.632 6.46l.11 1.1H3.395l.11-1.1c.266-2.66 1.155-4.88 2.632-6.46zM12 4c-1.105 0-2 .9-2 2s.895 2 2 2 2-.9 2-2-.895-2-2-2zM8 6c0-2.21 1.791-4 4-4s4 1.79 4 4-1.791 4-4 4-4-1.79-4-4z"/></svg>
        <span class="y-nav-label">Profile</span>
      </a>
    </nav>

    <!-- Post button (decorative) -->
    <button class="y-post-btn">Post</button>

    <!-- Simulation info -->
    <div class="y-sim-info">
      <div class="y-sim-badge" :class="{ live: isLive }">
        <span class="y-sim-dot"></span>
        {{ isLive ? 'LIVE' : 'HISTORICAL' }}
      </div>
      <div class="y-sim-id">{{ simulationId }}</div>
    </div>
  </div>
</template>

<script setup>
defineProps({
  simulationId: { type: String, default: '' },
  isLive: { type: Boolean, default: false }
})
</script>

<style scoped>
.y-sidebar {
  position: sticky;
  top: 0;
  height: 100vh;
  display: flex;
  flex-direction: column;
  padding: 12px 12px 20px;
  box-sizing: border-box;
}

.y-logo {
  font-size: 32px;
  font-weight: 900;
  color: #E7E9EA;
  padding: 12px 16px;
  letter-spacing: -1px;
  font-family: 'Space Grotesk', system-ui, sans-serif;
}

.y-nav {
  display: flex;
  flex-direction: column;
  gap: 4px;
  margin-top: 8px;
}

.y-nav-item {
  display: flex;
  align-items: center;
  gap: 20px;
  padding: 12px 16px;
  border-radius: 9999px;
  color: #E7E9EA;
  text-decoration: none;
  transition: background-color 0.2s;
  cursor: pointer;
}

.y-nav-item:hover {
  background-color: #1D1F23;
}

.y-nav-item.active {
  font-weight: 700;
}

.y-nav-icon {
  width: 26px;
  height: 26px;
  fill: #E7E9EA;
  flex-shrink: 0;
}

.y-nav-label {
  font-size: 20px;
  font-family: 'Space Grotesk', system-ui, sans-serif;
}

.y-post-btn {
  margin-top: 16px;
  width: 100%;
  padding: 16px;
  background: #1D9BF0;
  color: #fff;
  border: none;
  border-radius: 9999px;
  font-size: 17px;
  font-weight: 700;
  font-family: 'Space Grotesk', system-ui, sans-serif;
  cursor: default;
}

.y-sim-info {
  margin-top: auto;
  padding: 12px 16px;
}

.y-sim-badge {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 4px 10px;
  border-radius: 4px;
  background: #16181C;
  color: #71767B;
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 0.05em;
  font-family: 'JetBrains Mono', monospace;
}

.y-sim-badge.live {
  color: #00BA7C;
}

.y-sim-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: #71767B;
}

.y-sim-badge.live .y-sim-dot {
  background: #00BA7C;
  animation: pulse 2s infinite;
}

@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.4; }
}

.y-sim-id {
  margin-top: 6px;
  font-size: 12px;
  color: #71767B;
  font-family: 'JetBrains Mono', monospace;
  word-break: break-all;
}
</style>
