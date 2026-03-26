# 联邦训练前端改动说明：补上节点数 `nodeCount`

这份文档是给前端侧 Codex / 开发同学看的，目标只有一个：

- 把联邦训练任务里的“节点数”参数补到前端创建、展示和联调链路里。

## 1. 背景

后端已经补上了联邦训练任务的 `nodeCount` 字段。

这个字段表示：

- 本次 Flower 联邦训练使用的节点数
- 对应 Flower 本地模拟里的 `num-supernodes`

现在前端如果还按旧参数提交，会少传一个必填字段，创建任务会失败。

## 2. 前端必须改的地方

前端至少要改 4 处：

1. 创建任务表单增加 `nodeCount`
2. 调用 `POST /api/fl-tasks` 时把 `nodeCount` 一起传给后端
3. 任务列表页展示 `nodeCount`
4. 任务详情页展示 `nodeCount`

## 3. 接口变更

### 3.1 创建任务请求

接口：

- `POST /api/fl-tasks`

新增请求字段：

- `nodeCount: number`

请求示例：

```json
{
  "name": "yolo-voc-smoke-001",
  "taskType": "detection",
  "datasetName": "sample-1000-new",
  "datasetPath": "linux_flower_demo/allDatasets/sample-1000-new",
  "datasetFormat": "VOC",
  "modelSource": "linux_flower_demo/weights/yolov8n.pt",
  "numRounds": 3,
  "nodeCount": 2,
  "localEpochs": 1,
  "batchSize": 8,
  "learningRate": 0.01,
  "fractionEvaluate": 1.0
}
```

约束：

- 必填
- 必须是整数
- 必须大于 0

### 3.2 列表接口返回

接口：

- `GET /api/fl-tasks`

每条任务记录现在会多一个字段：

- `nodeCount`

返回片段示例：

```json
{
  "taskId": "fl_20260318210000_ab12cd",
  "name": "yolo-voc-smoke-001",
  "status": "RUNNING",
  "taskType": "detection",
  "numRounds": 5,
  "nodeCount": 2,
  "currentRound": 2,
  "progressPercent": 40
}
```

### 3.3 详情接口返回

接口：

- `GET /api/fl-tasks/{taskId}`

详情数据现在也会多一个字段：

- `nodeCount`

返回片段示例：

```json
{
  "taskId": "fl_20260318210000_ab12cd",
  "name": "yolo-voc-smoke-001",
  "status": "RUNNING",
  "taskType": "detection",
  "numRounds": 5,
  "nodeCount": 2,
  "currentRound": 2,
  "progressPercent": 40
}
```

## 4. 创建页要怎么改

建议在训练参数区新增一个字段：

- 标签名：`节点数`
- 字段名：`nodeCount`
- 组件：数字输入框或下拉框

建议默认值：

- `2`

建议校验：

- 必填
- 只能输入正整数
- 最小值 `1`

建议提示文案：

- `联邦训练参与节点数，对应 Flower 模拟节点数`

如果当前页面已经有“联邦轮数”“本地 epoch”“batch size”等参数区，就把 `nodeCount` 放在 `numRounds` 后面，保持同一组训练参数的阅读顺序。

## 5. 列表页要怎么改

任务列表建议增加一列：

- `节点数`

展示规则：

- 正常显示后端返回的 `nodeCount`
- 如果是历史任务，`nodeCount` 可能为 `null`，前端不要报错
- 历史数据建议展示为 `-`

## 6. 详情页要怎么改

详情页基础信息区建议增加一项：

- `节点数：{nodeCount}`

兼容规则：

- `nodeCount != null` 时正常显示
- `nodeCount == null` 时显示 `-`

## 7. 类型定义要同步

如果前端有 TypeScript 类型或接口定义，需要把 `nodeCount` 加进去。

例如任务创建参数：

```ts
type FlTaskCreateRequest = {
  name: string;
  taskType: string;
  datasetName: string;
  datasetPath: string;
  datasetFormat: string;
  modelSource: string;
  numRounds: number;
  nodeCount: number;
  localEpochs: number;
  batchSize: number;
  learningRate: number;
  fractionEvaluate: number;
};
```

例如任务详情 / 列表项：

```ts
type FlTaskView = {
  taskId: string;
  name: string;
  status: string;
  taskType: string;
  numRounds: number | null;
  nodeCount: number | null;
  currentRound: number | null;
  progressPercent: number | null;
};
```

## 8. 不需要改的地方

这次前端不用改这些：

- 启动接口路径
- 停止接口路径
- 轮次指标接口
- 轮询机制
- WebSocket

也就是说，接口路径还是原来的：

- `POST /api/fl-tasks`
- `POST /api/fl-tasks/{taskId}/start`
- `POST /api/fl-tasks/{taskId}/stop`
- `GET /api/fl-tasks`
- `GET /api/fl-tasks/{taskId}`
- `GET /api/fl-tasks/{taskId}/rounds`

变化只是在任务参数和任务展示字段里多了一个 `nodeCount`。

## 9. 前端验收标准

前端改完后，至少应满足下面几点：

1. 创建任务时页面可填写 `nodeCount`
2. 提交创建请求时 payload 中包含 `nodeCount`
3. 不传 `nodeCount` 时，前端表单校验应先拦住
4. 任务列表能显示 `nodeCount`
5. 任务详情能显示 `nodeCount`
6. 历史任务 `nodeCount=null` 时页面不报错


