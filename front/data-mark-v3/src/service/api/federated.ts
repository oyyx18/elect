import { request } from '../request'

export type FlTaskStatus = 'CREATED' | 'RUNNING' | 'COMPLETED' | 'FAILED' | 'STOPPED'

export type FlMetricMap = Record<string, number | null>

export interface FlRunnerHealth {
  ok: boolean
  running: boolean
  activeTaskId: string | null
  appDir: string
  runsDir: string
  datasetsRoot: string
}

export interface FlDataset {
  name: string
  path: string
  format: string
}

export interface FlTaskItem {
  taskId: string
  name: string
  status: FlTaskStatus
  taskType: string
  datasetName: string
  datasetPath: string
  datasetFormat: string
  modelSource: string
  numRounds: number | null
  nodeCount: number | null
  currentRound: number | null
  progressPercent: number | null
  finalMetricName: string | null
  finalMetricValue: number | null
  latestMetrics: FlMetricMap | null
  finalMetrics: FlMetricMap | null
  finalModelPath: string | null
  workDir: string | null
  errorMessage: string | null
  createdAt: string | null
  startedAt: string | null
  finishedAt: string | null
}

export interface FlTaskListResult {
  total: number
  current: number
  size: number
  records: FlTaskItem[]
}

export interface FlTaskRoundMetric {
  roundNo: number
  loss: number | null
  primaryMetric: number | null
  metrics: FlMetricMap
  createdAt: string | null
}

export interface FetchFlTasksParams {
  status?: FlTaskStatus | ''
  name?: string
  page?: number
  size?: number
}

export interface CreateFlTaskPayload {
  name: string
  taskType: 'detection' | 'classification'
  datasetName: string
  datasetPath: string
  datasetFormat: string
  modelSource: string
  numRounds: number
  nodeCount: number
  localEpochs: number
  batchSize: number
  learningRate: number
  fractionEvaluate: number
}

export interface FlTaskActionResult {
  taskId: string
  status: FlTaskStatus
  currentRound?: number
}

export function fetchFlRunnerHealth() {
  return request<FlRunnerHealth>({
    url: '/api/fl-runner/health',
    method: 'get'
  })
}

export function fetchFlDatasets() {
  return request<FlDataset[]>({
    url: '/api/fl-datasets',
    method: 'get'
  })
}

export function fetchFlTasks(params?: FetchFlTasksParams) {
  return request<FlTaskListResult>({
    url: '/api/fl-tasks',
    method: 'get',
    params
  })
}

export function createFlTask(data: CreateFlTaskPayload) {
  return request<FlTaskItem>({
    url: '/api/fl-tasks',
    method: 'post',
    data
  })
}

export function fetchFlTaskDetail(taskId: string) {
  return request<FlTaskItem>({
    url: `/api/fl-tasks/${taskId}`,
    method: 'get'
  })
}

export function fetchFlTaskRounds(taskId: string) {
  return request<FlTaskRoundMetric[]>({
    url: `/api/fl-tasks/${taskId}/rounds`,
    method: 'get'
  })
}

export function startFlTask(taskId: string) {
  return request<FlTaskActionResult>({
    url: `/api/fl-tasks/${taskId}/start`,
    method: 'post'
  })
}

export function stopFlTask(taskId: string) {
  return request<FlTaskActionResult>({
    url: `/api/fl-tasks/${taskId}/stop`,
    method: 'post'
  })
}
