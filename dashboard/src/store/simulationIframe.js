import { reactive } from 'vue'

// Global iframe state — lives in App.vue, controlled by SimulationPipelineView
export const simIframe = reactive({
  url: null,
  visible: false,
})
