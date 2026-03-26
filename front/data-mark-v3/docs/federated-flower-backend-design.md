# Flower 训练任务后端重设计（V1）

## 1. 目标

这个版本只解决 5 件事：

1. 前端可以创建训练任务，并填写基础训练参数和数据集信息。
2. 后端可以启动、停止、查询训练任务。
3. 后端可以看到每一轮的聚合指标。
4. 训练结束后，后端可以拿到最终指标和模型文件路径。
5. 整个方案尽量简单，能跑通，不做复杂调度。

明确不做的事：

- 不沿用现有 `/federated/**` 接口。
- 不做节点注册、心跳、多租户、多策略切换。
- 不做 WebSocket，前端轮询即可。
- 不让 Java 直接猜 Flower 进程状态，也不靠解析零散日志判断训练结果。

## 2. 推荐的最小架构

建议拆成两个后端角色：

1. `Spring Boot`
   - 面向前端提供业务接口。
   - 保存任务、轮次指标、最终结果。
   - 调用 Python 执行器启动或停止 Flower。
   - 定时同步运行中任务的状态和轮次指标。

2. `Python Flower 执行器`
   - 只负责执行训练。
   - 负责启动 `flwr run` 子进程。
   - 为每个任务创建独立工作目录。
   - 把训练状态、每轮指标、最终结果写成结构化文件。
   - 提供少量内部 HTTP 接口给 Java 读取。

3. `Flower App`
   - 继续保留 `linux_flower_demo/fl/client_app.py` 和 `linux_flower_demo/fl/server_app.py`。
   - 只做训练和评估。
   - 不直接承担“任务管理系统”的职责。

一句话概括边界：

- Java 管任务。
- Python 管进程。
- Flower 管训练。

## 3. 为什么这样拆

当前实现的核心问题不是字段不够，而是职责混乱：

1. Java 现在只会远程调 `/start` `/stop`，拿不到真正的任务级状态。
2. Python 现在只有一个全局 `_PROCESS`，没有任务隔离。
3. `server_app.py` 只把最终模型写到固定文件，缺少任务目录和结构化结果。
4. 每轮指标没有稳定出口，后端没法可靠展示训练曲线。

新方案里，Java 不再直接理解 Flower 内部细节，而是只和“Python 执行器”对接。这样实现成本低，而且边界清晰。

## 4. 任务生命周期

任务状态建议只保留这几个：

- `CREATED`：任务已创建，未启动
- `RUNNING`：训练中
- `COMPLETED`：训练完成
- `FAILED`：训练失败
- `STOPPED`：手动停止

V1 建议限制：

- 同一个 Python 执行器同一时刻只允许 1 个 `RUNNING` 任务

原因很简单：

- 这个项目是简单项目
- Flower 本地模拟本身就吃资源
- 单任务运行最容易稳定落地

如果以后需要并发，再加队列或多执行器实例。

## 5. 任务工作目录

每个任务必须有独立目录，例如：

```text
linux_flower_demo/runs/{taskId}/
  task.json
  status.json
  round_metrics.jsonl
  summary.json
  train.log
  final_model.pt
```

各文件职责：

- `task.json`：本次任务的配置快照
- `status.json`：当前状态、当前轮次、错误信息
- `round_metrics.jsonl`：每轮一条 JSON，给后端画曲线
- `summary.json`：最终指标、模型路径、开始结束时间
- `train.log`：原始 stdout/stderr，排障用
- `final_model.pt`：最终模型

重点是：后端看结构化文件，不靠日志字符串猜。

## 6. 数据库设计

V1 只建议两张表。

### 6.1 `fl_task`

建议字段：

```text
id
task_id
name
status
task_type
dataset_name
dataset_path
dataset_format
model_source
num_rounds
node_count
current_round
local_epochs
batch_size
learning_rate
fraction_evaluate
final_metric_name
final_metric_value
final_metrics_json
work_dir
final_model_path
error_message
config_json
created_at
started_at
finished_at
updated_at
```

说明：

- `config_json` 保存原始请求快照，避免后续字段变动导致任务难复现
- `final_metrics_json` 保存完整最终结果，页面只取最关注的主指标展示

### 6.2 `fl_task_round_metric`

建议字段：

```text
id
task_id
round_no
loss
primary_metric
metrics_json
created_at
```

说明：

- `primary_metric` 对分类任务可放 `accuracy`
- 对检测任务可放 `map50`
- 其余指标如 `precision`、`recall`、`map` 放进 `metrics_json`

V1 不建议把所有日志也塞数据库，日志保留文件即可。

## 7. 前端到 Java 的接口

新接口建议统一改成：

```text
/api/fl-tasks/**
```

### 7.1 创建任务

`POST /api/fl-tasks`

请求示例：

```json
{
  "name": "yolo-demo-001",
  "taskType": "detection",
  "datasetName": "sample-1000-new",
  "datasetPath": "linux_flower_demo/allDatasets/sample-1000-new",
  "datasetFormat": "VOC",
  "modelSource": "linux_flower_demo/weights/yolov8n.pt",
  "numRounds": 5,
  "nodeCount": 2,
  "localEpochs": 1,
  "batchSize": 8,
  "learningRate": 0.01,
  "fractionEvaluate": 1.0
}
```

返回示例：

```json
{
  "taskId": "fl_20260314_001",
  "status": "CREATED"
}
```

说明：

- 创建接口只落库，不立即启动
- 这样用户可以先保存，再手动启动

### 7.2 启动任务

`POST /api/fl-tasks/{taskId}/start`

返回示例：

```json
{
  "taskId": "fl_20260314_001",
  "status": "RUNNING"
}
```

### 7.3 停止任务

`POST /api/fl-tasks/{taskId}/stop`

返回示例：

```json
{
  "taskId": "fl_20260314_001",
  "status": "STOPPED"
}
```

### 7.4 任务列表

`GET /api/fl-tasks`

查询参数建议：

- `status`
- `name`
- `page`
- `size`

列表项只返回摘要：

- 任务名
- 状态
- 当前轮次
- 总轮次
- 主指标
- 创建时间

### 7.5 任务详情

`GET /api/fl-tasks/{taskId}`

返回示例：

```json
{
  "taskId": "fl_20260314_001",
  "name": "yolo-demo-001",
  "status": "RUNNING",
  "taskType": "detection",
  "datasetName": "sample-1000-new",
  "numRounds": 5,
  "nodeCount": 2,
  "currentRound": 2,
  "progressPercent": 40,
  "latestMetrics": {
    "map50": 0.73,
    "precision": 0.76,
    "recall": 0.69,
    "loss": 0.42
  },
  "finalMetrics": null,
  "finalModelPath": null,
  "errorMessage": null,
  "createdAt": "2026-03-14T10:00:00",
  "startedAt": "2026-03-14T10:01:00",
  "finishedAt": null
}
```

### 7.6 查询每轮指标

`GET /api/fl-tasks/{taskId}/rounds`

返回示例：

```json
[
  {
    "roundNo": 1,
    "loss": 0.58,
    "primaryMetric": 0.61,
    "metrics": {
      "map50": 0.61,
      "precision": 0.66,
      "recall": 0.54
    }
  },
  {
    "roundNo": 2,
    "loss": 0.42,
    "primaryMetric": 0.73,
    "metrics": {
      "map50": 0.73,
      "precision": 0.76,
      "recall": 0.69
    }
  }
]
```

### 7.7 数据集列表

`GET /api/fl-datasets`

用途：

- 创建任务页面下拉选择数据集
- 后端可以从固定根目录扫描，返回目录名和绝对路径

V1 返回字段建议：

```json
[
  {
    "name": "sample-1000-new",
    "path": "linux_flower_demo/allDatasets/sample-1000-new",
    "format": "VOC"
  }
]
```

## 8. Java 到 Python 执行器的内部接口

这套接口不直接给前端用，只给 Java 调用。

前缀建议：

```text
/runner/tasks/**
```

### 8.1 启动任务

`POST /runner/tasks`

请求示例：

```json
{
  "taskId": "fl_20260314_001",
  "workDir": "linux_flower_demo/runs/fl_20260314_001",
  "runConfig": {
    "task-type": "detection",
    "num-server-rounds": 5,
    "node-count": 2,
    "local-epochs": 1,
    "learning-rate": 0.01,
    "batch-size": 8,
    "fraction-evaluate": 1.0
  },
  "federationConfig": {
    "options.num-supernodes": 2
  },
  "env": {
    "FLOWER_DETECTION_DATASET": "linux_flower_demo/allDatasets/sample-1000-new",
    "FLOWER_YOLO_MODEL": "linux_flower_demo/weights/yolov8n.pt",
    "FLOWER_TASK_ID": "fl_20260314_001",
    "FLOWER_TASK_DIR": "linux_flower_demo/runs/fl_20260314_001"
  }
}
```

返回示例：

```json
{
  "taskId": "fl_20260314_001",
  "status": "RUNNING",
  "pid": 12345
}
```

### 8.2 查询任务状态

`GET /runner/tasks/{taskId}`

返回示例：

```json
{
  "taskId": "fl_20260314_001",
  "status": "RUNNING",
  "currentRound": 2,
  "numRounds": 5,
  "latestMetrics": {
    "map50": 0.73,
    "precision": 0.76,
    "recall": 0.69,
    "loss": 0.42
  },
  "finalMetrics": null,
  "finalModelPath": null,
  "errorMessage": null,
  "startedAt": "2026-03-14T10:01:00",
  "finishedAt": null
}
```

### 8.3 查询新轮次指标

`GET /runner/tasks/{taskId}/rounds?afterRound=2`

返回示例：

```json
{
  "taskId": "fl_20260314_001",
  "items": [
    {
      "roundNo": 3,
      "metrics": {
        "map50": 0.79,
        "precision": 0.81,
        "recall": 0.75,
        "loss": 0.31
      }
    }
  ]
}
```

### 8.4 停止任务

`POST /runner/tasks/{taskId}/stop`

### 8.5 健康检查

`GET /health`

## 9. 交互流程

### 9.1 创建任务

1. 前端调用 `POST /api/fl-tasks`
2. Java 校验参数
3. Java 写入 `fl_task`，状态为 `CREATED`
4. Java 返回 `taskId`

### 9.2 启动任务

1. 前端调用 `POST /api/fl-tasks/{taskId}/start`
2. Java 读取任务配置快照
3. Java 调用 Python `POST /runner/tasks`
4. Python 创建任务目录，写入 `task.json`
5. Python 启动 `flwr run`
6. Java 把任务状态改为 `RUNNING`

### 9.3 运行中同步

1. Java 定时任务每 3 到 5 秒轮询一次所有 `RUNNING` 任务
2. 调用 Python `GET /runner/tasks/{taskId}`
3. 再调用 `GET /runner/tasks/{taskId}/rounds?afterRound=n`
4. Java 增量写入 `fl_task_round_metric`
5. Java 更新 `fl_task.current_round`、`final_metrics_json`
6. 前端继续轮询 Java 的详情和轮次接口

这样就够了，不需要 WebSocket。

### 9.4 停止任务

1. 前端调用 `POST /api/fl-tasks/{taskId}/stop`
2. Java 调用 Python 停止接口
3. Python 终止子进程，写 `status.json` 和 `summary.json`
4. Java 更新任务状态为 `STOPPED`

## 10. Python 侧需要改的点

这个方案的关键不是重写 Flower，而是补上任务级结构化输出。

### 10.1 改造 `flower_server_api.py`

当前文件的问题：

- 只有全局 `_PROCESS`
- 没有任务目录
- 只有 `/start` `/stop` `/status`
- 不能返回每轮指标

建议改成“执行器 API”，最少做这些事：

1. 接收 `taskId`、`workDir`、`runConfig`、`env`
2. 启动 `flwr run linux_flower_demo --run-config ...`
3. stdout/stderr 落到 `train.log`
4. 根据 `status.json`、`round_metrics.jsonl`、`summary.json` 组装查询接口
5. 停止时终止当前子进程并更新状态

### 10.2 改造 `fl/server_app.py`

当前文件已经有 `global_evaluate(server_round, arrays)`，这是最合适的每轮指标出口。

建议增加两个能力：

1. 每轮评估后，把结果追加写入 `round_metrics.jsonl`
2. 训练完成后，把最终结果写入 `summary.json`

建议增加的环境变量：

```text
FLOWER_TASK_ID
FLOWER_TASK_DIR
FLOWER_ROUND_METRICS_FILE
FLOWER_STATUS_FILE
FLOWER_SUMMARY_FILE
FLOWER_FINAL_MODEL_PATH
```

### 10.3 输出格式建议

每轮指标一行 JSON：

```json
{
  "roundNo": 2,
  "metrics": {
    "map50": 0.73,
    "precision": 0.76,
    "recall": 0.69,
    "loss": 0.42
  },
  "timestamp": "2026-03-14T10:03:00"
}
```

最终汇总：

```json
{
  "taskId": "fl_20260314_001",
  "status": "COMPLETED",
  "finalMetrics": {
    "map50": 0.82,
    "precision": 0.84,
    "recall": 0.78,
    "loss": 0.25
  },
  "finalModelPath": "linux_flower_demo/runs/fl_20260314_001/final_model.pt",
  "startedAt": "2026-03-14T10:01:00",
  "finishedAt": "2026-03-14T10:10:00"
}
```

## 11. 参数设计建议

V1 不要把参数做得太多，前端表单建议只暴露这些：

- 任务名称
- 任务类型：`classification` / `detection`
- 数据集
- 模型权重路径
- 联邦轮数 `numRounds`
- 节点数 `nodeCount`
- 本地 epoch `localEpochs`
- batch size
- learning rate
- 评估比例 `fractionEvaluate`

先不要暴露这些：

- 自定义策略
- 最小客户端数
- 动态资源调度
- 多任务并发数

原因：这些参数当前项目里并没有稳定的执行基础，先做只会增加复杂度。

## 12. 前端展示建议

V1 页面只需要 3 个视图：

1. 任务列表
   - 名称
   - 状态
   - 当前轮次
   - 主指标
   - 创建时间

2. 创建任务页
   - 参数表单
   - 数据集下拉
   - 启动按钮

3. 任务详情页
   - 基础信息
   - 当前状态
   - 每轮指标折线图
   - 最终指标
   - 模型路径
   - 错误信息

详情页用 3 到 5 秒轮询一次就够了。

## 13. 最小实现顺序

建议按下面顺序做，最稳：

1. 先重写 Python 执行器接口，支持“启动任务 + 查询状态 + 停止任务”
2. 再改 `server_app.py`，把每轮指标和最终结果写到结构化文件
3. 再在 Java 里新建 `fl_task` 和 `fl_task_round_metric` 两张表
4. 再实现新的 `/api/fl-tasks/**` 接口
5. 最后加一个 Java 定时同步任务，把 Python 状态同步回数据库

## 14. 一句话结论

这个项目最合适的做法不是让 Java 直接控制 Flower 细节，而是：

- Java 负责任务中心和前端接口
- Python 负责执行 Flower 和产出结构化结果
- 前端只轮询 Java

这样改动最少，边界最清晰，也最容易先跑通。
