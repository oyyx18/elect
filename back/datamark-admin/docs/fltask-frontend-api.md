# Flower 训练任务前端接口文档

适用范围：前端页面调用 Spring Boot 提供的训练任务接口。

注意：前端只调用 `/api/**`，不要直接调用 Python Runner 的 `/runner/**` 接口。

## 1. 基本说明

当前训练任务模块的公开接口基于以下路径：

- `/api/fl-datasets`
- `/api/fl-tasks`
- `/api/fl-runner/health`

当前状态枚举：

- `CREATED`：任务已创建，未启动
- `RUNNING`：训练中
- `COMPLETED`：训练完成
- `FAILED`：训练失败
- `STOPPED`：手动停止

当前约束：

- 同一时刻只允许 1 个训练任务处于 `RUNNING`
- 创建任务不会自动启动，前端需要单独调启动接口
- `datasetPath` 必须使用后端 `/api/fl-datasets` 返回的值，不要让用户手填本机路径
- `finalModelPath`、`workDir` 都是服务器侧路径，前端只展示，不要当作浏览器本地路径使用
- 当前优先支持目标检测任务 `taskType=detection`
- `classification` 还在使用内置 CIFAR-10 流程，前端如果不打算联调这部分，建议先隐藏

## 2. 统一返回格式

所有接口都使用统一包装：

```json
{
  "code": 200,
  "message": "成功",
  "data": {}
}
```

失败示例：

```json
{
  "code": 500,
  "message": "Only CREATED tasks can be started",
  "data": null
}
```

说明：

- `code=200` 表示成功
- `code=500` 表示业务失败或内部异常
- 前端判断是否成功，优先看 `code`

## 3. 推荐页面流程

推荐前端调用顺序：

1. 页面加载时先调 `GET /api/fl-runner/health`
2. 创建页加载数据集下拉框时调 `GET /api/fl-datasets`
3. 用户填写参数后调 `POST /api/fl-tasks`
4. 用户点击启动后调 `POST /api/fl-tasks/{taskId}/start`
5. 列表页调 `GET /api/fl-tasks`
6. 详情页调 `GET /api/fl-tasks/{taskId}`
7. 详情页图表调 `GET /api/fl-tasks/{taskId}/rounds`
8. 训练中每 5 秒轮询一次详情和轮次接口

## 4. 接口清单

### 4.1 检查 Runner 状态

`GET /api/fl-runner/health`

用途：

- 判断 Java 后端是否已经连上 Python Runner
- 可在训练页面顶部展示“训练服务在线/离线”

成功返回示例：

```json
{
  "code": 200,
  "message": "成功",
  "data": {
    "ok": true,
    "running": false,
    "activeTaskId": null,
    "appDir": "/home/ouyangyuxuan/flowertest/linux_flower_demo",
    "runsDir": "/home/ouyangyuxuan/flowertest/linux_flower_demo/runs",
    "datasetsRoot": "/home/ouyangyuxuan/flowertest/linux_flower_demo/allDatasets"
  }
}
```

字段说明：

- `ok`：Runner 是否可访问
- `running`：当前是否有任务在训练
- `activeTaskId`：当前运行中的任务 ID，没有则为 `null`

### 4.2 获取数据集列表

`GET /api/fl-datasets`

用途：

- 用于创建任务页的数据集下拉框

成功返回示例：

```json
{
  "code": 200,
  "message": "成功",
  "data": [
    {
      "name": "dian",
      "path": "linux_flower_demo/allDatasets/dian",
      "format": "YOLO"
    },
    {
      "name": "sample-1000-new",
      "path": "linux_flower_demo/allDatasets/sample-1000-new",
      "format": "VOC"
    }
  ]
}
```

字段说明：

- `name`：数据集名称，前端展示用
- `path`：创建任务时原样回传给后端
- `format`：当前数据集格式，可选值主要为 `VOC`、`YOLO`

前端约束：

- `datasetPath` 和 `datasetFormat` 建议直接取这一接口的返回值
- 不建议让用户自由输入 `datasetPath`

### 4.3 创建任务

`POST /api/fl-tasks`

请求体：

```json
{
  "name": "yolo-voc-smoke-001",
  "taskType": "detection",
  "datasetName": "sample-1000-new",
  "datasetPath": "linux_flower_demo/allDatasets/sample-1000-new",
  "datasetFormat": "VOC",
  "modelSource": "linux_flower_demo/weights/yolov8n.pt",
  "numRounds": 1,
  "nodeCount": 2,
  "localEpochs": 1,
  "batchSize": 8,
  "learningRate": 0.01,
  "fractionEvaluate": 1.0
}
```

字段说明：

- `name`：任务名称，必填
- `taskType`：任务类型，当前建议使用 `detection`
- `datasetName`：数据集名称，建议使用数据集接口返回值
- `datasetPath`：数据集路径，必填，建议使用数据集接口返回值
- `datasetFormat`：数据集格式，建议使用数据集接口返回值
- `modelSource`：预训练模型路径，当前可默认写死为 `linux_flower_demo/weights/yolov8n.pt`
- `numRounds`：联邦轮数，必须大于 0
- `nodeCount`：联邦节点数，必须大于 0，对应 Flower 本地模拟的 `num-supernodes`
- `localEpochs`：本地训练 epoch，必须大于 0
- `batchSize`：批大小，必须大于 0
- `learningRate`：学习率，必须大于 0
- `fractionEvaluate`：评估客户端比例，必须大于等于 0

成功返回示例：

```json
{
  "code": 200,
  "message": "成功",
  "data": {
    "taskId": "fl_20260318210000_ab12cd",
    "name": "yolo-voc-smoke-001",
    "status": "CREATED",
    "taskType": "detection",
    "datasetName": "sample-1000-new",
    "datasetPath": "linux_flower_demo/allDatasets/sample-1000-new",
    "datasetFormat": "VOC",
    "modelSource": "linux_flower_demo/weights/yolov8n.pt",
    "numRounds": 1,
    "nodeCount": 2,
    "currentRound": 0,
    "progressPercent": 0,
    "finalMetricName": null,
    "finalMetricValue": null,
    "latestMetrics": null,
    "finalMetrics": null,
    "finalModelPath": null,
    "workDir": "linux_flower_demo/runs/fl_20260318210000_ab12cd",
    "errorMessage": null,
    "createdAt": "2026-03-18T21:00:00",
    "startedAt": null,
    "finishedAt": null
  }
}
```

前端处理建议：

- 创建成功后跳转到任务详情页
- 不要假设创建后会自动训练

### 4.4 启动任务

`POST /api/fl-tasks/{taskId}/start`

路径参数：

- `taskId`：任务 ID

成功返回示例：

```json
{
  "code": 200,
  "message": "成功",
  "data": {
    "taskId": "fl_20260318210000_ab12cd",
    "status": "RUNNING",
    "currentRound": 0
  }
}
```

失败场景：

- 任务不存在
- 任务不是 `CREATED`
- 已有其他任务在运行

前端处理建议：

- 启动成功后立即开始轮询详情接口
- 如果失败，直接展示 `message`

### 4.5 停止任务

`POST /api/fl-tasks/{taskId}/stop`

路径参数：

- `taskId`：任务 ID

成功返回示例：

```json
{
  "code": 200,
  "message": "成功",
  "data": {
    "taskId": "fl_20260318210000_ab12cd",
    "status": "STOPPED"
  }
}
```

前端处理建议：

- 仅在 `RUNNING` 时展示“停止训练”按钮
- 停止后继续刷新一次详情页，拿最终状态

### 4.6 获取任务列表

`GET /api/fl-tasks`

查询参数：

- `status`：可选，按状态过滤
- `name`：可选，按任务名模糊搜索
- `page`：可选，默认 `1`
- `size`：可选，默认 `10`

请求示例：

```text
/api/fl-tasks?page=1&size=10&status=RUNNING
```

成功返回示例：

```json
{
  "code": 200,
  "message": "成功",
  "data": {
    "total": 2,
    "current": 1,
    "size": 10,
    "records": [
      {
        "taskId": "fl_20260318210000_ab12cd",
        "name": "yolo-voc-smoke-001",
        "status": "RUNNING",
        "taskType": "detection",
        "datasetName": "sample-1000-new",
        "datasetPath": "linux_flower_demo/allDatasets/sample-1000-new",
        "datasetFormat": "VOC",
        "modelSource": "linux_flower_demo/weights/yolov8n.pt",
        "numRounds": 5,
        "nodeCount": 2,
        "currentRound": 2,
        "progressPercent": 40,
        "finalMetricName": "map50",
        "finalMetricValue": 0.73,
        "latestMetrics": {
          "map50": 0.73,
          "precision": 0.76,
          "recall": 0.69,
          "loss": 0.42
        },
        "finalMetrics": null,
        "finalModelPath": null,
        "workDir": "linux_flower_demo/runs/fl_20260318210000_ab12cd",
        "errorMessage": null,
        "createdAt": "2026-03-18T21:00:00",
        "startedAt": "2026-03-18T21:01:00",
        "finishedAt": null
      }
    ]
  }
}
```

前端展示建议：

- 列表页建议展示：任务名称、任务类型、数据集、状态、当前轮次、总轮次、主指标、创建时间
- `progressPercent` 可直接用于进度条

### 4.7 获取任务详情

`GET /api/fl-tasks/{taskId}`

路径参数：

- `taskId`：任务 ID

成功返回示例：

```json
{
  "code": 200,
  "message": "成功",
  "data": {
    "taskId": "fl_20260318210000_ab12cd",
    "name": "yolo-voc-smoke-001",
    "status": "RUNNING",
    "taskType": "detection",
    "datasetName": "sample-1000-new",
    "datasetPath": "linux_flower_demo/allDatasets/sample-1000-new",
    "datasetFormat": "VOC",
    "modelSource": "linux_flower_demo/weights/yolov8n.pt",
    "numRounds": 5,
    "nodeCount": 2,
    "currentRound": 2,
    "progressPercent": 40,
    "finalMetricName": "map50",
    "finalMetricValue": 0.73,
    "latestMetrics": {
      "map50": 0.73,
      "precision": 0.76,
      "recall": 0.69,
      "loss": 0.42
    },
    "finalMetrics": null,
    "finalModelPath": null,
    "workDir": "linux_flower_demo/runs/fl_20260318210000_ab12cd",
    "errorMessage": null,
    "createdAt": "2026-03-18T21:00:00",
    "startedAt": "2026-03-18T21:01:00",
    "finishedAt": null
  }
}
```

字段说明：

- `progressPercent`：0 到 100 的整数，可直接用于进度条
- `finalMetricName`：主指标名称，检测任务通常为 `map50`
- `finalMetricValue`：主指标值
- `latestMetrics`：最近一轮指标
- `finalMetrics`：训练结束后的最终指标
- `finalModelPath`：最终模型服务器路径
- `errorMessage`：失败原因

前端处理建议：

- `RUNNING` 时每 5 秒轮询一次
- `COMPLETED`、`FAILED`、`STOPPED` 后停止轮询
- 如果 `errorMessage` 不为空，应在详情页明显展示

### 4.8 获取每轮指标

`GET /api/fl-tasks/{taskId}/rounds`

路径参数：

- `taskId`：任务 ID

成功返回示例：

```json
{
  "code": 200,
  "message": "成功",
  "data": [
    {
      "roundNo": 1,
      "loss": 0.58,
      "primaryMetric": 0.61,
      "metrics": {
        "map50": 0.61,
        "precision": 0.67,
        "recall": 0.55,
        "loss": 0.58
      },
      "createdAt": "2026-03-18T21:02:30"
    },
    {
      "roundNo": 2,
      "loss": 0.42,
      "primaryMetric": 0.73,
      "metrics": {
        "map50": 0.73,
        "precision": 0.76,
        "recall": 0.69,
        "loss": 0.42
      },
      "createdAt": "2026-03-18T21:04:10"
    }
  ]
}
```

字段说明：

- `roundNo`：轮次
- `loss`：当前轮损失
- `primaryMetric`：主指标值
- `metrics`：该轮完整指标字典
- `createdAt`：该轮指标入库时间

前端展示建议：

- 折线图至少画 `loss` 和 `primaryMetric`
- 检测任务可额外画 `map50`、`precision`、`recall`

## 5. 字段约束建议

前端创建任务时建议做基础校验：

- `name` 必填
- `taskType` 必填
- `datasetName` 必填
- `datasetPath` 必填
- `datasetFormat` 必填
- `numRounds > 0`
- `nodeCount > 0`
- `localEpochs > 0`
- `batchSize > 0`
- `learningRate > 0`
- `fractionEvaluate >= 0`

推荐默认值：

- `taskType`: `detection`
- `modelSource`: `linux_flower_demo/weights/yolov8n.pt`
- `numRounds`: `1` 或 `3`
- `nodeCount`: `2`
- `localEpochs`: `1`
- `batchSize`: `8`
- `learningRate`: `0.01`
- `fractionEvaluate`: `1.0`

## 6. 前端实现建议

创建页建议：

- 先加载数据集列表
- 选择数据集后自动回填 `datasetName`、`datasetPath`、`datasetFormat`
- `modelSource` 可先做成默认值输入框

列表页建议：

- 支持按 `status` 和 `name` 检索
- 对 `RUNNING` 任务做醒目状态展示

详情页建议：

- 分为“基础信息”“当前状态”“每轮指标图表”“错误信息”四块
- `RUNNING` 时轮询任务详情和轮次指标
- `FAILED` 时重点展示 `errorMessage`

## 7. 当前已知限制

- 同一时刻只能运行一个训练任务
- `classification` 自定义数据集流程还未对齐，前端如无明确需求，建议先只开放 `detection`
- 目前没有模型文件下载接口，`finalModelPath` 仅用于展示和后续扩展
- 当前没有 WebSocket，训练进度请使用轮询
