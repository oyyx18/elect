<script lang="ts">
export default {
  name: 'FlTaskConsole'
}
</script>

<script setup lang="ts">
import { computed, h, nextTick, onBeforeUnmount, onMounted, reactive, ref, watch } from 'vue'
import type { LocationQueryValue } from 'vue-router'
import { useRoute, useRouter } from 'vue-router'
import dayjs from 'dayjs'
import { AddOutline, PlayOutline, RefreshOutline, SearchOutline, StopOutline } from '@vicons/ionicons5'
import { NButton, NSpace, NTag, useDialog, useMessage, type DataTableColumns, type FormRules, type TagProps } from 'naive-ui'
import { useEcharts, type ECOption } from '@/hooks/common/echarts'
import { useNaiveForm } from '@/hooks/common/form'
import {
  createFlTask,
  fetchFlDatasets,
  fetchFlRunnerHealth,
  fetchFlTaskDetail,
  fetchFlTaskRounds,
  fetchFlTasks,
  startFlTask,
  stopFlTask,
  type CreateFlTaskPayload,
  type FlDataset,
  type FlMetricMap,
  type FlRunnerHealth,
  type FlTaskItem,
  type FlTaskRoundMetric,
  type FlTaskStatus
} from '@/service/api/federated'

const DEFAULT_MODEL_SOURCE = 'linux_flower_demo/weights/yolov8n.pt'
const POLL_INTERVAL = 5000
const STALE_TASK_SYNC_MESSAGE = '训练实际上已经结束，当前任务已按停止状态显示。如果仍然无法启动新任务，请先同步后端运行器状态。'
const STALE_TASK_REFRESHED_MESSAGE = '训练实际上已经结束，页面状态已刷新。'

const route = useRoute()
const router = useRouter()
const message = useMessage()
const dialog = useDialog()

const runnerHealth = ref<FlRunnerHealth | null>(null)
const datasets = ref<FlDataset[]>([])
const taskList = ref<FlTaskItem[]>([])
const selectedTask = ref<FlTaskItem | null>(null)
const roundMetrics = ref<FlTaskRoundMetric[]>([])

const runnerLoading = ref(false)
const datasetsLoading = ref(false)
const taskListLoading = ref(false)
const detailLoading = ref(false)
const roundLoading = ref(false)
const refreshing = ref(false)
const createTaskBusy = ref(false)
const pollBusy = ref(false)
const taskAction = ref<{ taskId: string; action: 'start' | 'stop' } | null>(null)

const filters = reactive({
  name: '',
  status: '' as FlTaskStatus | ''
})

const pagination = reactive({
  page: 1,
  size: 10,
  total: 0
})

const createTaskModalVisible = ref(false)
const { formRef: createTaskFormRef, validate: validateCreateTaskForm, restoreValidation: restoreCreateTaskValidation } = useNaiveForm()

const createTaskForm = reactive({
  name: '',
  datasetPath: '',
  modelSource: DEFAULT_MODEL_SOURCE,
  numRounds: 3,
  nodeCount: 2,
  localEpochs: 1,
  batchSize: 8,
  learningRate: 0.01,
  fractionEvaluate: 1
})

function createPositiveNumberRule(label: string): App.Global.FormRule {
  return {
    required: true,
    type: 'number',
    trigger: ['blur', 'input'],
    validator: (_rule, value) => Number(value) > 0,
    message: `${label}必须大于 0`
  }
}

function createPositiveIntegerRule(label: string): App.Global.FormRule {
  return {
    required: true,
    type: 'number',
    trigger: ['blur', 'input'],
    validator: (_rule, value) => Number.isInteger(Number(value)) && Number(value) > 0,
    message: `${label}必须为大于 0 的整数`
  }
}

function createMinimumIntegerRule(label: string, min: number): App.Global.FormRule {
  return {
    required: true,
    type: 'number',
    trigger: ['blur', 'input'],
    validator: (_rule, value) => Number.isInteger(Number(value)) && Number(value) >= min,
    message: `${label}必须为大于或等于 ${min} 的整数`
  }
}

function createNonNegativeNumberRule(label: string): App.Global.FormRule {
  return {
    required: true,
    type: 'number',
    trigger: ['blur', 'input'],
    validator: (_rule, value) => Number(value) >= 0,
    message: `${label}必须大于或等于 0`
  }
}

const createTaskRules: FormRules = {
  name: [{ required: true, message: '请输入任务名称', trigger: ['blur', 'input'] }],
  datasetPath: [{ required: true, message: '请选择数据集', trigger: ['change', 'blur'] }],
  modelSource: [{ required: true, message: '请输入模型路径', trigger: ['blur', 'input'] }],
  numRounds: [createPositiveIntegerRule('联邦轮次')],
  nodeCount: [createMinimumIntegerRule('节点数量', 2)],
  localEpochs: [createPositiveIntegerRule('本地训练轮数')],
  batchSize: [createPositiveIntegerRule('批大小')],
  learningRate: [createPositiveNumberRule('学习率')],
  fractionEvaluate: [createNonNegativeNumberRule('评估比例')]
}

const statusOptions = [
  { label: '全部状态', value: '' },
  { label: '已创建', value: 'CREATED' },
  { label: '运行中', value: 'RUNNING' },
  { label: '已完成', value: 'COMPLETED' },
  { label: '失败', value: 'FAILED' },
  { label: '已停止', value: 'STOPPED' }
]

const datasetOptions = computed(() =>
  datasets.value.map(item => ({
    label: `${item.name} / ${item.format}`,
    value: item.path
  }))
)

const selectedDataset = computed(() => datasets.value.find(item => item.path === createTaskForm.datasetPath) ?? null)
const selectedTaskId = computed(() => normalizeRouteTaskId(route.query.taskId))
const runnerOnline = computed(() => Boolean(runnerHealth.value?.ok))
const selectedTaskEffectiveStatus = computed<FlTaskStatus | null>(() =>
  selectedTask.value ? getEffectiveTaskStatus(selectedTask.value) : null
)
const selectedTaskStatusMeta = computed(() =>
  selectedTaskEffectiveStatus.value ? getStatusMeta(selectedTaskEffectiveStatus.value) : null
)
const selectedTaskStatusDesynced = computed(
  () => Boolean(selectedTask.value && selectedTask.value.status === 'RUNNING' && selectedTaskEffectiveStatus.value === 'STOPPED')
)
const shouldPoll = computed(() => Boolean(runnerHealth.value?.running || selectedTaskEffectiveStatus.value === 'RUNNING'))
const listEmpty = computed(() => !taskListLoading.value && !taskList.value.length)

const latestMetricEntries = computed(() => buildMetricEntries(selectedTask.value?.latestMetrics))
const finalMetricEntries = computed(() => buildMetricEntries(selectedTask.value?.finalMetrics))

const currentPrimaryMetric = computed(() => {
  const task = selectedTask.value
  if (!task) return null

  const metricName = task.finalMetricName || 'primaryMetric'
  const fromFinalMetric = task.finalMetricValue
  const fromLatestMetric = task.finalMetricName ? task.latestMetrics?.[task.finalMetricName] ?? null : null
  const fromRounds = getLastRound()?.primaryMetric ?? null
  const value = fromFinalMetric ?? fromLatestMetric ?? fromRounds

  if (value == null) return null

  return {
    label: metricName,
    value
  }
})

const latestLossMetric = computed(() => {
  const fromLatest = selectedTask.value?.latestMetrics?.loss ?? null
  return fromLatest ?? getLastRound()?.loss ?? null
})

const summaryCards = computed(() => [
  {
    label: '运行器状态',
    value: runnerOnline.value ? '在线' : '离线',
    hint: runnerHealth.value?.running ? `运行中任务：${runnerHealth.value.activeTaskId}` : '当前没有运行中的任务'
  },
  {
    label: '数据集数量',
    value: `${datasets.value.length}`,
    hint: datasetsLoading.value ? '数据集加载中' : '创建任务时请选择数据集'
  },
  {
    label: '任务总数',
    value: `${pagination.total}`,
    hint: '支持按状态和任务名称筛选'
  },
  {
    label: '当前查看',
    value: selectedTask.value?.name || '未选择任务',
    hint: selectedTask.value?.taskId || '请从列表中选择任务'
  }
])

const { domRef: roundChartRef, setOptions: setRoundChartOptions } = useEcharts(() => buildRoundChartOptions())

let pollTimer: ReturnType<typeof setInterval> | null = null

watch(
  () => route.query.taskId,
  async value => {
    const taskId = normalizeRouteTaskId(value)

    if (!taskId) {
      selectedTask.value = null
      roundMetrics.value = []
      return
    }

    await Promise.all([loadTaskDetail(taskId), loadTaskRounds(taskId)])
  },
  { immediate: true }
)

watch(
  () => [roundMetrics.value, selectedTask.value?.taskId, selectedTask.value?.finalMetricName],
  async () => {
    await nextTick()
    setRoundChartOptions(buildRoundChartOptions())
  },
  { deep: true }
)

const taskColumns: DataTableColumns<FlTaskItem> = [
  {
    title: '任务',
    key: 'name',
    minWidth: 230,
    render: row =>
      h('div', { class: 'task-name-cell' }, [
        h('div', { class: 'task-name-title' }, row.name),
        h('div', { class: 'task-name-id' }, row.taskId)
      ])
  },
  {
    title: '状态',
    key: 'status',
    width: 120,
    render: row => {
      const meta = getStatusMeta(getEffectiveTaskStatus(row))
      return h(
        NTag,
        {
          type: meta.type,
          bordered: false
        },
        { default: () => meta.label }
      )
    }
  },
  {
    title: '数据集',
    key: 'datasetName',
    minWidth: 160
  },
  {
    title: '进度',
    key: 'progressPercent',
    width: 110,
    render: row => `${row.progressPercent ?? 0}%`
  },
  {
    title: '轮次',
    key: 'currentRound',
    width: 120,
    render: row => `${row.currentRound ?? 0} / ${row.numRounds ?? 0}`
  },
  {
    title: '节点数',
    key: 'nodeCount',
    width: 100,
    render: row => row.nodeCount ?? '-'
  },
  {
    title: '主指标',
    key: 'finalMetricValue',
    width: 130,
    render: row => formatMetricValue(row.finalMetricValue, row.finalMetricName || undefined)
  },
  {
    title: '创建时间',
    key: 'createdAt',
    width: 170,
    render: row => formatDateTime(row.createdAt)
  },
  {
    title: '操作',
    key: 'actions',
    width: 230,
    align: 'center',
    render: row =>
      h(
        NSpace,
        {
          justify: 'center',
          wrap: false
        },
        {
          default: () => [
            h(
              NButton,
              {
                size: 'small',
                quaternary: true,
                type: selectedTaskId.value === row.taskId ? 'primary' : 'default',
                onClick: () => handleSelectTask(row.taskId)
              },
              { default: () => '详情' }
            ),
            h(
              NButton,
              {
                size: 'small',
                type: 'primary',
                tertiary: true,
                disabled: !canStartTask(row),
                loading: isTaskActionLoading(row.taskId, 'start'),
                onClick: () => handleStartTask(row)
              },
              { default: () => '启动' }
            ),
            h(
              NButton,
              {
                size: 'small',
                type: 'warning',
                tertiary: true,
                disabled: getEffectiveTaskStatus(row) !== 'RUNNING',
                loading: isTaskActionLoading(row.taskId, 'stop'),
                onClick: () => handleStopTask(row)
              },
              { default: () => '停止' }
            )
          ]
        }
      )
  }
]

const roundColumns: DataTableColumns<FlTaskRoundMetric> = [
  {
    title: '轮次',
    key: 'roundNo',
    width: 90
  },
  {
    title: '损失',
    key: 'loss',
    width: 120,
    render: row => formatMetricValue(row.loss, 'loss')
  },
  {
    title: '主指标',
    key: 'primaryMetric',
    width: 120,
    render: row => formatMetricValue(row.primaryMetric, selectedTask.value?.finalMetricName || undefined)
  },
  {
    title: '指标详情',
    key: 'metrics',
    minWidth: 280,
    render: row => serializeMetrics(row.metrics)
  },
  {
    title: '更新时间',
    key: 'createdAt',
    width: 170,
    render: row => formatDateTime(row.createdAt)
  }
]

function normalizeRouteTaskId(value: LocationQueryValue | LocationQueryValue[] | undefined) {
  if (Array.isArray(value)) return value[0] ?? null
  return value ?? null
}

function resetCreateTaskForm() {
  createTaskForm.name = ''
  createTaskForm.datasetPath = ''
  createTaskForm.modelSource = DEFAULT_MODEL_SOURCE
  createTaskForm.numRounds = 3
  createTaskForm.nodeCount = 2
  createTaskForm.localEpochs = 1
  createTaskForm.batchSize = 8
  createTaskForm.learningRate = 0.01
  createTaskForm.fractionEvaluate = 1
}

function openCreateTaskModal() {
  resetCreateTaskForm()
  restoreCreateTaskValidation()
  createTaskModalVisible.value = true
}

function closeCreateTaskModal() {
  createTaskModalVisible.value = false
  restoreCreateTaskValidation()
}

function getStatusMeta(status: FlTaskStatus): { label: string; type: TagProps['type'] } {
  const statusMap: Record<FlTaskStatus, { label: string; type: TagProps['type'] }> = {
    CREATED: { label: '已创建', type: 'default' },
    RUNNING: { label: '运行中', type: 'success' },
    COMPLETED: { label: '已完成', type: 'info' },
    FAILED: { label: '失败', type: 'error' },
    STOPPED: { label: '已停止', type: 'warning' }
  }

  return statusMap[status]
}

function getEffectiveTaskStatus(task: Pick<FlTaskItem, 'taskId' | 'status'>): FlTaskStatus {
  if (runnerHealth.value?.ok !== true) return task.status
  if (task.status !== 'RUNNING') return task.status
  if (runnerHealth.value.running && runnerHealth.value.activeTaskId === task.taskId) return 'RUNNING'
  return 'STOPPED'
}

function getTaskRuntimeResolution(taskId: string): 'RUNNING' | 'STOPPED' | 'UNKNOWN' {
  const currentTask =
    selectedTask.value?.taskId === taskId
      ? selectedTask.value
      : taskList.value.find(item => item.taskId === taskId) ?? null

  if (currentTask) {
    return getEffectiveTaskStatus(currentTask) === 'RUNNING' ? 'RUNNING' : 'STOPPED'
  }

  if (runnerHealth.value?.ok !== true) return 'UNKNOWN'
  if (!runnerHealth.value.running) return 'STOPPED'

  return runnerHealth.value.activeTaskId === taskId ? 'RUNNING' : 'STOPPED'
}

function formatDateTime(value: string | null | undefined) {
  if (!value) return '-'
  return dayjs(value).format('YYYY-MM-DD HH:mm:ss')
}

function formatMetricLabel(key: string) {
  const labelMap: Record<string, string> = {
    primaryMetric: '主指标',
    map50: 'mAP50',
    map: 'mAP',
    precision: '精确率',
    recall: '召回率',
    loss: '损失'
  }

  return labelMap[key] || key
}

function formatTaskType(taskType: string | null | undefined) {
  const labelMap: Record<string, string> = {
    detection: '目标检测'
  }

  if (!taskType) return '-'
  return labelMap[taskType.toLowerCase()] || taskType
}

function formatMetricValue(value: number | null | undefined, metricName?: string) {
  if (value == null || Number.isNaN(Number(value))) return '-'

  const metricKey = metricName?.toLowerCase() || ''
  if (metricKey.includes('loss')) {
    return Number(value).toFixed(4)
  }

  if (value >= 0 && value <= 1) {
    return `${(value * 100).toFixed(2)}%`
  }

  return Number(value).toFixed(4)
}

function buildMetricEntries(metrics?: FlMetricMap | null) {
  if (!metrics) return []

  return Object.entries(metrics)
    .filter(([, value]) => value != null)
    .map(([key, value]) => ({
      key,
      label: formatMetricLabel(key),
      value: value as number
    }))
}

function serializeMetrics(metrics?: FlMetricMap | null) {
  if (!metrics) return '-'

  const items = Object.entries(metrics)
    .filter(([, value]) => value != null)
    .map(([key, value]) => `${formatMetricLabel(key)}: ${formatMetricValue(value as number, key)}`)

  return items.length ? items.join(' / ') : '-'
}

function getLastRound() {
  return roundMetrics.value[roundMetrics.value.length - 1] ?? null
}

function setTaskQuery(taskId: string | null) {
  const nextQuery = { ...route.query }

  if (taskId) nextQuery.taskId = taskId
  else delete nextQuery.taskId

  router.replace({ query: nextQuery })
}

function pickDefaultTaskId(records: FlTaskItem[]) {
  const activeTaskId = runnerHealth.value?.activeTaskId
  if (activeTaskId && records.some(item => item.taskId === activeTaskId)) return activeTaskId
  return records[0]?.taskId ?? null
}

function canStartTask(task: FlTaskItem) {
  if (task.status !== 'CREATED') return false
  if (runnerHealth.value?.ok === false) return false
  if (!runnerHealth.value?.running) return true
  return runnerHealth.value.activeTaskId === task.taskId
}

function isTaskActionLoading(taskId: string, action: 'start' | 'stop') {
  return taskAction.value?.taskId === taskId && taskAction.value?.action === action
}

function handleSelectTask(taskId: string) {
  setTaskQuery(taskId)
}

function handleSearch() {
  pagination.page = 1
  loadTaskList()
}

function handleResetFilters() {
  filters.name = ''
  filters.status = ''
  pagination.page = 1
  loadTaskList()
}

function handlePageChange(page: number) {
  pagination.page = page
  loadTaskList()
}

function handlePageSizeChange(size: number) {
  pagination.page = 1
  pagination.size = size
  loadTaskList()
}

async function loadRunnerHealth(showBusy = true) {
  if (showBusy) runnerLoading.value = true

  try {
    const { data, error } = await fetchFlRunnerHealth()
    if (!error && data) {
      runnerHealth.value = data
    }
  } finally {
    if (showBusy) runnerLoading.value = false
  }
}

async function loadDatasets(showBusy = true) {
  if (showBusy) datasetsLoading.value = true

  try {
    const { data, error } = await fetchFlDatasets()
    if (!error) {
      datasets.value = data || []
    }
  } finally {
    if (showBusy) datasetsLoading.value = false
  }
}

async function loadTaskList(showBusy = true) {
  if (showBusy) taskListLoading.value = true

  try {
    const { data, error } = await fetchFlTasks({
      page: pagination.page,
      size: pagination.size,
      name: filters.name.trim() || undefined,
      status: filters.status || undefined
    })

    if (!error && data) {
      taskList.value = data.records || []
      pagination.total = data.total || 0
      pagination.page = data.current || pagination.page
      pagination.size = data.size || pagination.size

      if (!selectedTaskId.value && taskList.value.length) {
        const defaultTaskId = pickDefaultTaskId(taskList.value)
        if (defaultTaskId) setTaskQuery(defaultTaskId)
      }
    }
  } finally {
    if (showBusy) taskListLoading.value = false
  }
}

async function loadTaskDetail(taskId: string, showBusy = true) {
  if (showBusy) detailLoading.value = true

  try {
    const { data, error } = await fetchFlTaskDetail(taskId)
    if (!error) {
      selectedTask.value = data || null
    }
  } finally {
    if (showBusy) detailLoading.value = false
  }
}

async function loadTaskRounds(taskId: string, showBusy = true) {
  if (showBusy) roundLoading.value = true

  try {
    const { data, error } = await fetchFlTaskRounds(taskId)
    if (!error) {
      roundMetrics.value = data || []
    }
  } finally {
    if (showBusy) roundLoading.value = false
  }
}

async function refreshAll() {
  refreshing.value = true

  try {
    await Promise.all([loadRunnerHealth(false), loadDatasets(false), loadTaskList(false)])

    if (selectedTaskId.value) {
      await Promise.all([loadTaskDetail(selectedTaskId.value, false), loadTaskRounds(selectedTaskId.value, false)])
    }
  } finally {
    refreshing.value = false
  }
}

async function handleCreateTask() {
  await validateCreateTaskForm()

  if (!selectedDataset.value) {
    message.error('请选择有效的数据集')
    return
  }

  createTaskBusy.value = true

  try {
    const payload: CreateFlTaskPayload = {
      name: createTaskForm.name.trim(),
      taskType: 'detection',
      datasetName: selectedDataset.value.name,
      datasetPath: selectedDataset.value.path,
      datasetFormat: selectedDataset.value.format,
      modelSource: createTaskForm.modelSource.trim(),
      numRounds: createTaskForm.numRounds,
      nodeCount: createTaskForm.nodeCount,
      localEpochs: createTaskForm.localEpochs,
      batchSize: createTaskForm.batchSize,
      learningRate: createTaskForm.learningRate,
      fractionEvaluate: createTaskForm.fractionEvaluate
    }

    const { data, error } = await createFlTask(payload)
    if (error || !data) return

    message.success('任务创建成功')
    closeCreateTaskModal()
    pagination.page = 1

    await Promise.all([loadRunnerHealth(false), loadTaskList(false)])
    setTaskQuery(data.taskId)
  } finally {
    createTaskBusy.value = false
  }
}

async function handleStartTask(task: FlTaskItem) {
  if (!canStartTask(task)) return

  taskAction.value = { taskId: task.taskId, action: 'start' }

  try {
    const { error } = await startFlTask(task.taskId)
    if (error) return

    message.success('任务已启动')
    setTaskQuery(task.taskId)
    await refreshAll()
  } finally {
    taskAction.value = null
  }
}

async function executeStopTask(taskId: string) {
  taskAction.value = { taskId, action: 'stop' }

  try {
    const { error } = await stopFlTask(taskId)
    if (error) {
      await refreshAll()

      if (getTaskRuntimeResolution(taskId) === 'STOPPED') {
        message.info(STALE_TASK_REFRESHED_MESSAGE)
      }

      return
    }

    message.success('训练已停止')
    await refreshAll()
  } finally {
    taskAction.value = null
  }
}

function handleStopTask(task: FlTaskItem) {
  if (getEffectiveTaskStatus(task) !== 'RUNNING') return

  dialog.warning({
    title: '停止训练',
    content: `确认停止任务“${task.name}”吗？`,
    positiveText: '停止训练',
    negativeText: '取消',
    onPositiveClick: () => executeStopTask(task.taskId)
  })
}

async function handlePoll() {
  if (!shouldPoll.value || pollBusy.value) return

  pollBusy.value = true

  try {
    await Promise.all([loadRunnerHealth(false), loadTaskList(false)])

    if (selectedTaskId.value) {
      await Promise.all([loadTaskDetail(selectedTaskId.value, false), loadTaskRounds(selectedTaskId.value, false)])
    }
  } finally {
    pollBusy.value = false
  }
}

function buildRoundChartOptions(): ECOption {
  const rounds = roundMetrics.value
  const roundLabels = rounds.map(item => `第${item.roundNo}轮`)
  const palette = ['#0f766e', '#2563eb', '#ea580c', '#9333ea', '#dc2626', '#0891b2']
  const primaryMetricKey = selectedTask.value?.finalMetricName || 'primaryMetric'
  const additionalMetricKeys = Array.from(
    new Set(
      rounds.flatMap(item =>
        Object.entries(item.metrics || {})
          .filter(([, value]) => value != null)
          .map(([key]) => key)
      )
    )
  ).filter(key => key !== primaryMetricKey && key !== 'loss')

  const series = [
    {
      name: formatMetricLabel(primaryMetricKey),
      type: 'line' as const,
      smooth: true,
      symbolSize: 8,
      data: rounds.map(item => item.primaryMetric),
      lineStyle: {
        width: 3
      },
      itemStyle: {
        color: palette[0]
      }
    },
    {
      name: '损失',
      type: 'line' as const,
      smooth: true,
      symbolSize: 8,
      data: rounds.map(item => item.loss),
      lineStyle: {
        width: 2
      },
      itemStyle: {
        color: palette[1]
      }
    },
    ...additionalMetricKeys.map((key, index) => ({
      name: formatMetricLabel(key),
      type: 'line' as const,
      smooth: true,
      symbolSize: 7,
      data: rounds.map(item => item.metrics?.[key] ?? null),
      lineStyle: {
        width: 2
      },
      itemStyle: {
        color: palette[(index + 2) % palette.length]
      }
    }))
  ]

  return {
    color: palette,
    tooltip: {
      trigger: 'axis'
    },
    legend: {
      top: 0,
      data: series.map(item => item.name)
    },
    grid: {
      top: 48,
      left: 20,
      right: 20,
      bottom: 20,
      containLabel: true
    },
    xAxis: {
      type: 'category',
      boundaryGap: false,
      data: roundLabels
    },
    yAxis: {
      type: 'value',
      scale: true
    },
    series
  }
}

function rowClassName(row: FlTaskItem) {
  return row.taskId === selectedTaskId.value ? 'task-row--active' : ''
}

async function initConsole() {
  await Promise.all([loadRunnerHealth(), loadDatasets()])
  await loadTaskList()
}

onMounted(async () => {
  await initConsole()
  pollTimer = setInterval(handlePoll, POLL_INTERVAL)
})

onBeforeUnmount(() => {
  if (pollTimer) {
    clearInterval(pollTimer)
    pollTimer = null
  }
})
</script>

<template>
  <div class="fl-task-console">
    <n-card :bordered="false" class="hero-card">
      <div class="hero-panel">
        <div class="hero-copy">
          <div class="hero-label"></div>
          <div class="hero-title-row">
            <h2>联邦训练任务控制台</h2>
            <n-tag :type="runnerOnline ? 'success' : 'error'" round :bordered="false">
              {{ runnerOnline ? '运行器在线' : '运行器离线' }}
            </n-tag>
          </div>
          <p class="hero-desc">
            在一个页面内创建训练任务、控制训练生命周期，并查看训练指标与产物。
          </p>
          <div class="hero-actions">
            <n-button :loading="refreshing" @click="refreshAll">
              <template #icon>
                <n-icon :component="RefreshOutline" />
              </template>
              刷新
            </n-button>
            <n-button type="primary" @click="openCreateTaskModal">
              <template #icon>
                <n-icon :component="AddOutline" />
              </template>
              创建任务
            </n-button>
          </div>
        </div>

        <div class="hero-stat-grid">
          <div v-for="card in summaryCards" :key="card.label" class="summary-card">
            <span class="summary-label">{{ card.label }}</span>
            <strong class="summary-value">{{ card.value }}</strong>
            <span class="summary-hint">{{ card.hint }}</span>
          </div>
        </div>
      </div>

      <div class="runner-meta-grid">
        <div class="runner-meta-item">
          <span class="runner-meta-label">运行目录</span>
          <code>{{ runnerHealth?.runsDir || '-' }}</code>
        </div>
        <div class="runner-meta-item">
          <span class="runner-meta-label">应用目录</span>
          <code>{{ runnerHealth?.appDir || '-' }}</code>
        </div>
        <div class="runner-meta-item">
          <span class="runner-meta-label">数据集根目录</span>
          <code>{{ runnerHealth?.datasetsRoot || '-' }}</code>
        </div>
      </div>
    </n-card>

    <div class="workspace-grid">
      <n-card :bordered="false" title="训练任务" class="list-card">
        <template #header-extra>
          <n-button type="primary" secondary @click="openCreateTaskModal">
            <template #icon>
              <n-icon :component="AddOutline" />
            </template>
            新建任务
          </n-button>
        </template>

        <div class="toolbar">
          <n-input
            v-model:value="filters.name"
            clearable
            placeholder="按任务名称搜索"
            @keydown.enter="handleSearch"
          />
          <n-select
            v-model:value="filters.status"
            :options="statusOptions"
            clearable
            placeholder="按状态筛选"
          />
          <n-button type="primary" @click="handleSearch">
            <template #icon>
              <n-icon :component="SearchOutline" />
            </template>
            搜索
          </n-button>
          <n-button quaternary @click="handleResetFilters">重置</n-button>
        </div>

        <n-alert v-if="!runnerOnline" type="warning" show-icon class="mb-16px">
          运行器当前不可用。在后端重新连接 Python 运行器之前，创建任务或启动任务可能失败。
        </n-alert>

        <n-data-table
          :columns="taskColumns"
          :data="taskList"
          :loading="taskListLoading"
          :row-class-name="rowClassName"
          :row-key="row => row.taskId"
          :scroll-x="1280"
          :single-line="false"
          :bordered="false"
        />

        <n-empty v-if="listEmpty" description="暂无训练任务">
          <template #extra>
            <n-button type="primary" @click="openCreateTaskModal">创建首个任务</n-button>
          </template>
        </n-empty>

        <div class="pagination-row">
          <n-pagination
            v-model:page="pagination.page"
            v-model:page-size="pagination.size"
            :item-count="pagination.total"
            :page-sizes="[10, 20, 50]"
            show-size-picker
            @update:page="handlePageChange"
            @update:page-size="handlePageSizeChange"
          />
        </div>
      </n-card>

      <n-card :bordered="false" class="detail-card">
        <template #header>
          <div class="detail-header">
            <div>
              <div class="detail-title">{{ selectedTask?.name || '任务详情' }}</div>
              <div class="detail-subtitle">{{ selectedTask?.taskId || '请从列表中选择任务' }}</div>
            </div>
            <n-tag v-if="selectedTask" round :type="selectedTaskStatusMeta?.type" :bordered="false">
              {{ selectedTaskStatusMeta?.label }}
            </n-tag>
          </div>
        </template>

        <template #header-extra>
          <n-space v-if="selectedTask" :size="8">
            <n-button tertiary :loading="refreshing" @click="refreshAll">
              <template #icon>
                <n-icon :component="RefreshOutline" />
              </template>
              刷新详情
            </n-button>
            <n-button
              type="primary"
              :disabled="!canStartTask(selectedTask)"
              :loading="isTaskActionLoading(selectedTask.taskId, 'start')"
              @click="handleStartTask(selectedTask)"
            >
              <template #icon>
                <n-icon :component="PlayOutline" />
              </template>
              启动任务
            </n-button>
            <n-button
              type="warning"
              :disabled="selectedTaskEffectiveStatus !== 'RUNNING'"
              :loading="isTaskActionLoading(selectedTask.taskId, 'stop')"
              @click="handleStopTask(selectedTask)"
            >
              <template #icon>
                <n-icon :component="StopOutline" />
              </template>
              停止训练
            </n-button>
          </n-space>
        </template>

        <n-empty v-if="!selectedTask && !detailLoading" description="未选择任务">
          <template #extra>
            <n-button type="primary" @click="openCreateTaskModal">创建任务</n-button>
          </template>
        </n-empty>

        <n-spin v-else :show="detailLoading">
          <div class="detail-content">
            <n-alert v-if="selectedTask?.errorMessage" type="error" show-icon class="mb-16px">
              {{ selectedTask.errorMessage }}
            </n-alert>

            <n-alert v-if="selectedTaskStatusDesynced" type="warning" show-icon class="mb-16px">
              {{ STALE_TASK_SYNC_MESSAGE }}
            </n-alert>

            <div class="detail-summary-grid">
              <div class="detail-summary-card">
                <span class="detail-summary-label">训练进度</span>
                <strong class="detail-summary-value">{{ selectedTask?.progressPercent ?? 0 }}%</strong>
                <span class="detail-summary-hint">
                  {{ selectedTask?.currentRound ?? 0 }} / {{ selectedTask?.numRounds ?? 0 }} 轮
                </span>
              </div>
              <div class="detail-summary-card">
                <span class="detail-summary-label">主指标</span>
                <strong class="detail-summary-value">
                  {{ currentPrimaryMetric ? formatMetricValue(currentPrimaryMetric.value, currentPrimaryMetric.label) : '-' }}
                </strong>
                <span class="detail-summary-hint">
                  {{ currentPrimaryMetric ? formatMetricLabel(currentPrimaryMetric.label) : '等待首轮结果' }}
                </span>
              </div>
              <div class="detail-summary-card">
                <span class="detail-summary-label">最新损失</span>
                <strong class="detail-summary-value">{{ formatMetricValue(latestLossMetric, 'loss') }}</strong>
                <span class="detail-summary-hint">来自最近一轮或当前任务详情</span>
              </div>
              <div class="detail-summary-card">
                <span class="detail-summary-label">轮询</span>
                <strong class="detail-summary-value">{{ shouldPoll ? '每 5 秒刷新' : '已停止轮询' }}</strong>
                <span class="detail-summary-hint">任务进入最终状态后会停止自动刷新</span>
              </div>
            </div>

            <div class="progress-block">
              <div class="section-title">当前状态</div>
              <n-progress
                type="line"
                :percentage="selectedTask?.progressPercent ?? 0"
                :show-indicator="true"
                :height="18"
                :processing="selectedTaskEffectiveStatus === 'RUNNING'"
                status="success"
              />
            </div>

            <div class="section-block">
              <div class="section-title">基本信息</div>
              <n-descriptions bordered :column="2" label-placement="left">
                <n-descriptions-item label="任务类型">
                  {{ formatTaskType(selectedTask?.taskType) }}
                </n-descriptions-item>
                <n-descriptions-item label="节点数量">
                  {{ selectedTask?.nodeCount ?? '-' }}
                </n-descriptions-item>
                <n-descriptions-item label="数据集">
                  {{ selectedTask?.datasetName || '-' }} / {{ selectedTask?.datasetFormat || '-' }}
                </n-descriptions-item>
                <n-descriptions-item label="数据集路径">
                  <code>{{ selectedTask?.datasetPath || '-' }}</code>
                </n-descriptions-item>
                <n-descriptions-item label="模型路径">
                  <code>{{ selectedTask?.modelSource || '-' }}</code>
                </n-descriptions-item>
                <n-descriptions-item label="创建时间">
                  {{ formatDateTime(selectedTask?.createdAt) }}
                </n-descriptions-item>
                <n-descriptions-item label="开始时间">
                  {{ formatDateTime(selectedTask?.startedAt) }}
                </n-descriptions-item>
                <n-descriptions-item label="结束时间">
                  {{ formatDateTime(selectedTask?.finishedAt) }}
                </n-descriptions-item>
                <n-descriptions-item label="工作目录">
                  <code>{{ selectedTask?.workDir || '-' }}</code>
                </n-descriptions-item>
              </n-descriptions>
            </div>

            <div class="section-block">
              <div class="section-title">最新指标</div>
              <div v-if="latestMetricEntries.length" class="metric-chip-grid">
                <div v-for="item in latestMetricEntries" :key="item.key" class="metric-chip">
                  <span>{{ item.label }}</span>
                  <strong>{{ formatMetricValue(item.value, item.key) }}</strong>
                </div>
              </div>
              <n-empty v-else description="暂无轮次指标" />
            </div>

            <div class="section-block">
              <div class="section-title">轮次趋势</div>
              <div class="chart-shell">
                <div ref="roundChartRef" class="chart-canvas"></div>
                <div v-if="!roundMetrics.length && !roundLoading" class="chart-empty">
                  <n-empty description="暂无轮次指标" />
                </div>
              </div>
            </div>

            <div class="section-block">
              <div class="section-title">轮次详情</div>
              <n-data-table
                :columns="roundColumns"
                :data="roundMetrics"
                :loading="roundLoading"
                :scroll-x="820"
                :pagination="false"
                :bordered="false"
              />
            </div>

            <div class="section-block">
              <div class="section-title">最终结果</div>
              <div v-if="finalMetricEntries.length" class="metric-chip-grid">
                <div v-for="item in finalMetricEntries" :key="item.key" class="metric-chip">
                  <span>{{ item.label }}</span>
                  <strong>{{ formatMetricValue(item.value, item.key) }}</strong>
                </div>
              </div>
              <n-empty v-else description="暂无最终指标" />

              <div class="artifact-grid">
                <div class="artifact-box">
                  <span class="artifact-label">最终模型路径</span>
                  <code>{{ selectedTask?.finalModelPath || '-' }}</code>
                </div>
                <div class="artifact-box">
                  <span class="artifact-label">任务工作目录</span>
                  <code>{{ selectedTask?.workDir || '-' }}</code>
                </div>
              </div>
            </div>
          </div>
        </n-spin>
      </n-card>
    </div>

    <n-modal
      v-model:show="createTaskModalVisible"
      preset="card"
      title="创建联邦训练任务"
      style="width: 760px"
      :bordered="false"
      :segmented="{ content: true }"
      @close="closeCreateTaskModal"
    >
      <n-form
        ref="createTaskFormRef"
        :model="createTaskForm"
        :rules="createTaskRules"
        label-placement="left"
        label-width="110px"
      >
        <div class="form-grid">
          <n-form-item label="任务名称" path="name">
            <n-input v-model:value="createTaskForm.name" placeholder="例如：yolo-voc-smoke-001" />
          </n-form-item>

          <n-form-item label="任务类型">
            <n-input value="目标检测" readonly />
          </n-form-item>

          <n-form-item label="数据集" path="datasetPath">
            <n-select
              v-model:value="createTaskForm.datasetPath"
              :options="datasetOptions"
              :loading="datasetsLoading"
              placeholder="请选择数据集"
            />
          </n-form-item>

          <n-form-item label="数据集格式">
            <n-input :value="selectedDataset?.format || '-'" readonly />
          </n-form-item>

          <n-form-item label="模型路径" path="modelSource" class="form-span-2">
            <n-input v-model:value="createTaskForm.modelSource" placeholder="请输入预训练模型路径" />
          </n-form-item>

          <n-form-item label="联邦轮次" path="numRounds">
            <n-input-number v-model:value="createTaskForm.numRounds" :min="1" :precision="0" class="w-full" />
          </n-form-item>

          <n-form-item label="节点数量" path="nodeCount">
            <n-input-number v-model:value="createTaskForm.nodeCount" :min="2" :precision="0" class="w-full" />
          </n-form-item>

          <n-form-item label="本地训练轮数" path="localEpochs">
            <n-input-number v-model:value="createTaskForm.localEpochs" :min="1" :precision="0" class="w-full" />
          </n-form-item>

          <n-form-item label="批大小" path="batchSize">
            <n-input-number v-model:value="createTaskForm.batchSize" :min="1" :precision="0" class="w-full" />
          </n-form-item>

          <n-form-item label="学习率" path="learningRate">
            <n-input-number
              v-model:value="createTaskForm.learningRate"
              :min="0.0001"
              :step="0.0001"
              class="w-full"
            />
          </n-form-item>

          <n-form-item label="评估比例" path="fractionEvaluate">
            <n-input-number
              v-model:value="createTaskForm.fractionEvaluate"
              :min="0"
              :step="0.1"
              class="w-full"
            />
          </n-form-item>
        </div>
      </n-form>

      <template #footer>
        <n-space justify="end">
          <n-button @click="closeCreateTaskModal">取消</n-button>
          <n-button type="primary" :loading="createTaskBusy" @click="handleCreateTask">
            创建并查看详情
          </n-button>
        </n-space>
      </template>
    </n-modal>
  </div>
</template>

<style scoped>
.fl-task-console {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.hero-card :deep(.n-card__content) {
  padding: 0;
}

.hero-panel {
  position: relative;
  display: grid;
  gap: 24px;
  padding: 24px;
  color: #f8fafc;
  background:
    radial-gradient(circle at top right, rgb(255 255 255 / 0.18), transparent 28%),
    linear-gradient(135deg, #115e59 0%, #0f766e 42%, #164e63 100%);
}

.hero-copy {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.hero-label {
  font-size: 12px;
  font-weight: 700;
  letter-spacing: 0.16em;
  text-transform: uppercase;
  opacity: 0.84;
}

.hero-title-row {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
  align-items: center;
}

.hero-title-row h2 {
  margin: 0;
  font-size: 28px;
  line-height: 1.2;
  font-weight: 700;
}

.hero-desc {
  margin: 0;
  max-width: 880px;
  line-height: 1.7;
  color: rgb(240 253 250 / 0.92);
}

.hero-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
}

.hero-stat-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 12px;
}

.summary-card {
  display: flex;
  flex-direction: column;
  gap: 8px;
  padding: 16px;
  border: 1px solid rgb(255 255 255 / 0.16);
  border-radius: 16px;
  background: rgb(255 255 255 / 0.08);
  backdrop-filter: blur(10px);
}

.summary-label {
  font-size: 12px;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: rgb(204 251 241 / 0.86);
}

.summary-value {
  font-size: 20px;
  line-height: 1.2;
  font-weight: 700;
  color: #fff;
}

.summary-hint {
  font-size: 12px;
  line-height: 1.6;
  color: rgb(224 242 254 / 0.84);
}

.runner-meta-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 12px;
  padding: 16px 24px 24px;
  background: #f8fafc;
}

.runner-meta-item {
  display: flex;
  flex-direction: column;
  gap: 8px;
  padding: 14px 16px;
  border: 1px solid #dbeafe;
  border-radius: 14px;
  background: linear-gradient(180deg, #fff 0%, #f8fafc 100%);
}

.runner-meta-label {
  font-size: 12px;
  font-weight: 600;
  color: #475569;
}

.runner-meta-item code {
  font-size: 12px;
  line-height: 1.6;
  word-break: break-all;
  color: #0f172a;
}

.workspace-grid {
  display: grid;
  grid-template-columns: minmax(420px, 1.05fr) minmax(460px, 1.35fr);
  gap: 16px;
  align-items: start;
}

.list-card,
.detail-card {
  min-height: 720px;
}

.toolbar {
  display: grid;
  grid-template-columns: minmax(0, 1.4fr) 180px auto auto;
  gap: 12px;
  margin-bottom: 16px;
}

.pagination-row {
  display: flex;
  justify-content: flex-end;
  margin-top: 16px;
}

.task-name-cell {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.task-name-title {
  font-weight: 600;
  color: #0f172a;
}

.task-name-id {
  font-size: 12px;
  color: #64748b;
}

.detail-header {
  display: flex;
  gap: 12px;
  align-items: center;
}

.detail-title {
  font-size: 18px;
  font-weight: 700;
  color: #0f172a;
}

.detail-subtitle {
  margin-top: 4px;
  font-size: 12px;
  color: #64748b;
}

.detail-content {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.detail-summary-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 12px;
}

.detail-summary-card {
  display: flex;
  flex-direction: column;
  gap: 8px;
  padding: 16px;
  border: 1px solid #dbeafe;
  border-radius: 16px;
  background: linear-gradient(180deg, #fff 0%, #f8fafc 100%);
}

.detail-summary-label {
  font-size: 12px;
  color: #475569;
}

.detail-summary-value {
  font-size: 20px;
  line-height: 1.2;
  font-weight: 700;
  color: #0f172a;
}

.detail-summary-hint {
  font-size: 12px;
  color: #64748b;
}

.progress-block,
.section-block {
  display: flex;
  flex-direction: column;
  gap: 12px;
  padding: 16px;
  border: 1px solid #e2e8f0;
  border-radius: 16px;
  background: #fff;
}

.section-title {
  font-size: 15px;
  font-weight: 700;
  color: #0f172a;
}

.metric-chip-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
  gap: 12px;
}

.metric-chip {
  display: flex;
  flex-direction: column;
  gap: 6px;
  padding: 14px 16px;
  border-radius: 14px;
  background: #f8fafc;
  border: 1px solid #e2e8f0;
}

.metric-chip span {
  font-size: 12px;
  color: #64748b;
}

.metric-chip strong {
  font-size: 16px;
  color: #0f172a;
}

.chart-shell {
  position: relative;
  min-height: 340px;
  border-radius: 14px;
  background: #f8fafc;
  overflow: hidden;
}

.chart-canvas {
  height: 340px;
  width: 100%;
}

.chart-empty {
  position: absolute;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgb(248 250 252 / 0.9);
}

.artifact-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px;
  margin-top: 12px;
}

.artifact-box {
  display: flex;
  flex-direction: column;
  gap: 8px;
  padding: 14px 16px;
  border: 1px solid #dbeafe;
  border-radius: 14px;
  background: linear-gradient(180deg, #eff6ff 0%, #f8fafc 100%);
}

.artifact-label {
  font-size: 12px;
  font-weight: 600;
  color: #475569;
}

.artifact-box code {
  font-size: 12px;
  line-height: 1.6;
  word-break: break-all;
  color: #0f172a;
}

.form-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 0 16px;
}

.form-span-2 {
  grid-column: span 2;
}

:deep(.task-row--active td) {
  background: #eff6ff !important;
}

@media (max-width: 1400px) {
  .hero-stat-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .detail-summary-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media (max-width: 1200px) {
  .workspace-grid {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 900px) {
  .toolbar {
    grid-template-columns: 1fr;
  }

  .runner-meta-grid,
  .detail-summary-grid,
  .artifact-grid,
  .form-grid,
  .hero-stat-grid {
    grid-template-columns: 1fr;
  }

  .form-span-2 {
    grid-column: auto;
  }
}
</style>
