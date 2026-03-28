/**
 * API client for MiroFish Backend direct calls (port 5001)
 * Used for heavy data: posts-feed, profiles, graph data, report sections
 */
import axios from 'axios'

const api = axios.create({
  baseURL: '/api',
  timeout: 300000,
  headers: { 'Content-Type': 'application/json' },
})

// ── Simulation Data ──

export function getPostsFeed(simulationId, limit = 50, offset = 0) {
  return api.get(`/simulation/${simulationId}/posts-feed`, {
    params: { platform: 'twitter', limit, offset },
  })
}

export function getRunStatus(simulationId) {
  return api.get(`/simulation/${simulationId}/run-status`)
}

export function getRunStatusDetail(simulationId) {
  return api.get(`/simulation/${simulationId}/run-status/detail`)
}

export function getSimulationProfiles(simulationId) {
  return api.get(`/simulation/${simulationId}/profiles`, {
    params: { platform: 'twitter' },
  })
}

export function getSimulationConfig(simulationId) {
  return api.get(`/simulation/${simulationId}/config`)
}

// ── Report Data ──

export function getReport(reportId) {
  return api.get(`/report/${reportId}`)
}

export function getReportBySimulation(simulationId) {
  return api.get(`/report/by-simulation/${simulationId}`)
}

export function getReportSection(reportId, sectionIndex) {
  return api.get(`/report/${reportId}/section/${sectionIndex}`)
}

// ── Graph Data ──

export function getGraphData(graphId) {
  return api.get(`/graph/data/${graphId}`)
}
