/**
 * API client for the Neuro-Trade Agent Server (port 8000)
 */
import axios from 'axios'

const api = axios.create({
  baseURL: '/api/agent',
  timeout: 300000,
  headers: { 'Content-Type': 'application/json' },
})

// ── Scanning ──

export function startScan(params = {}) {
  return api.post('/scan', params)
}

export function getScanStatus() {
  return api.get('/scan/status')
}

// ── Opportunities ──

export function getOpportunities(status = null) {
  const params = status ? { status } : {}
  return api.get('/opportunities', { params })
}

export function getOpportunity(id) {
  return api.get(`/opportunities/${id}`)
}

export function startSimulation(id) {
  return api.post(`/opportunities/${id}/start-simulation`)
}

export function syncMirofish(id) {
  return api.post(`/opportunities/${id}/sync-mirofish`)
}

export function analyzeReport(id) {
  return api.post(`/opportunities/${id}/analyze-report`)
}

export function rejectOpportunity(id) {
  return api.post(`/opportunities/${id}/reject`)
}

export function approveTrade(id) {
  return api.post(`/opportunities/${id}/approve-trade`)
}

export function rejectTrade(id) {
  return api.post(`/opportunities/${id}/reject-trade`)
}

// ── Portfolio ──

export function getPortfolio() {
  return api.get('/portfolio')
}

export function getTradeHistory(limit = 20) {
  return api.get('/portfolio/trades', { params: { limit } })
}

// ── SSE Event Stream ──

export function connectEventStream(lastId = 0) {
  return new EventSource(`/api/agent/stream?last_id=${lastId}`)
}

export function connectOpportunityStream(oppId, lastId = 0) {
  return new EventSource(`/api/agent/stream/${oppId}?last_id=${lastId}`)
}
