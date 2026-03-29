<template>
  <router-view />

  <!-- Persistent iframe — never unmounts, survives route changes -->
  <div v-if="simIframe.url" v-show="simIframe.visible" class="sim-iframe-layer">
    <div class="sim-iframe-toolbar">
      <button class="sim-iframe-back" @click="simIframe.visible = false">← Overview</button>
      <span class="sim-iframe-logo">NEURO-TRADE</span>
    </div>
    <iframe :src="simIframe.url" class="sim-iframe-content" />
  </div>
</template>

<script setup>
import { simIframe } from './store/simulationIframe'
</script>

<style>
.sim-iframe-layer {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  z-index: 1000;
  display: flex;
  flex-direction: column;
  background: #fff;
}
.sim-iframe-toolbar {
  height: 44px;
  background: #000;
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 0 16px;
  flex-shrink: 0;
}
.sim-iframe-back {
  background: none;
  border: 1px solid #444;
  color: #fff;
  font-size: 12px;
  padding: 4px 10px;
  border-radius: 4px;
  cursor: pointer;
  white-space: nowrap;
}
.sim-iframe-back:hover {
  background: #222;
}
.sim-iframe-logo {
  font-family: var(--font-mono, 'JetBrains Mono', monospace);
  font-size: 13px;
  font-weight: 800;
  letter-spacing: 2px;
  color: #fff;
}
.sim-iframe-content {
  flex: 1;
  width: 100%;
  border: none;
}
</style>
