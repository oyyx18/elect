# Flower 训练任务后端实际实现情况（V1）

本文不是新的设计稿，而是基于 [federated-flower-backend-design.md](./federated-flower-backend-design.md) 对当前代码实际落地情况的整理。

## 1. 目标

当前已经实际实现的目标：

1. 前端可以创建训练任务，并填写基础训练参数和数据集信息。
2. 后端可以启动、停止、查询训练任务。
3. 后端可以看到每一轮的聚合指标。
4. 训练结束后，后端可以拿到最终指标和模型文件路径。
5. 整体方案已经能按“简单项目”目标跑通基本链路。

当前也保持了设计中的约束：

- 没有继续沿用旧 `/federated/**` 接口。
- 没有做节点注册、心跳、多租户、多策略切换。
- 没有做 WebSocket，前端仍然按轮询方式对接。
- Java 不再直接管理 Flower 进程，而是通过 Python Runner 间接管理。

当前仍未完成的部分：

- `classification` 还没有按“自定义数据集”方式打通，仍在使用内置 CIFAR-10 流程。
- 模型文件下载接口还没有做，`finalModelPath` 目前只返回服务器侧路径。

## 2. 推荐的最小架构

设计中的三层结构已经基本落地。

### 2.1 `Spring Boot`

已实现：

- 面向前端提供训练任务接口。
- 使用数据库保存任务信息、轮次指标、最终结果。
- 通过 HTTP 调用远端 Python Runner。
- 定时同步运行中任务的状态和轮次指标。

当前实际代码位置：

- `src/main/java/com/qczy/fltask/controller`
- `src/main/java/com/qczy/fltask/service`
- `src/main/java/com/qczy/fltask/runner`
- `src/main/java/com/qczy/fltask/mapper`

### 2.2 `Python Flower 执行器`

已实现：

- 使用 `linux_flower_demo/flower_server_api.py` 作为任务型 Runner。
- 能启动训练子进程。
- 能为每个任务创建独立工作目录。
- 能把状态、轮次指标、最终结果写成结构化文件。
- 能通过内部 HTTP 接口把这些信息提供给 Java。

### 2.3 `Flower App`

已实现：

- 保留了 `linux_flower_demo/fl/client_app.py`
- 保留了 `linux_flower_demo/fl/server_app.py`
- 训练和评估逻辑仍在 Flower App 内部

当前补充实现：

- `server_app.py` 已经能写 `status.json`、`summary.json`、`round_metrics.jsonl`
- 检测任务 `linux_flower_demo/fl/detection/yolov8.py` 已支持 `VOC` 和 `YOLO`

一句话概括当前边界：

- Java 管任务与数据落库。
- Python Runner 管进程与运行目录。
- Flower App 管训练与评估。

## 3. 为什么这样拆

设计中提出的 4 个核心问题，当前都已经有对应落地：

1. Java 不再只会远程调简单的 `/start` `/stop`，而是已经能拿到任务级状态、轮次指标和最终结果。
2. Python 不再只有一个简单全局进程开关，而是已经有任务工作目录、任务索引和任务状态文件。
3. `server_app.py` 不再只写固定模型文件，而是已经按任务写结构化输出。
4. 每轮指标已经有稳定出口，Java 可定时同步并落库。

实际效果：

- 任务边界更清楚。
- 前后端接口更稳定。
- Java 和 Python 可以部署在不同机器。

## 4. 任务生命周期

当前已经使用的任务状态：

- `CREATED`
- `RUNNING`
- `COMPLETED`
- `FAILED`
- `STOPPED`

当前行为：

- 创建任务后，状态为 `CREATED`
- 启动后变为 `RUNNING`
- 正常完成后变为 `COMPLETED`
- 训练异常退出时变为 `FAILED`
- 手动停止后变为 `STOPPED`

当前限制也已经实现：

- 同一个 Python Runner 同一时刻只允许 1 个运行中任务
- Java 侧在启动任务前也会校验数据库里是否已有其他 `RUNNING` 任务

未实现的部分：

- 没有任务队列
- 没有并发调度
- 没有多 Runner 负载分发

## 5. 任务工作目录

当前已经按任务目录方式落地，目录结构与设计基本一致：

```text
linux_flower_demo/runs/{taskId}/
  task.json
  status.json
  round_metrics.jsonl
  summary.json
  train.log
  final_model.pt
```

当前各文件职责：

- `task.json`：保存本次任务的请求快照和实际执行命令
- `status.json`：保存任务当前状态、当前轮次、最近指标、最终指标、错误信息
- `round_metrics.jsonl`：保存每一轮的结构化指标
- `summary.json`：保存训练完成后的最终结果摘要
- `train.log`：保存 Flower 子进程的标准输出
- `final_model.pt`：保存最终模型

当前还有一个补充实现：

```text
linux_flower_demo/runs/.index/{taskId}.json
```

作用：

- 用于从 `taskId` 快速定位任务工作目录
- 支持任务进程结束后继续查询任务结果

## 6. 数据库设计

设计中的两张表已经实际建表并在代码中使用。

SQL 文件：

- `add_fl_task_tables.sql`

### 6.1 `fl_task`

已实现字段基本覆盖设计稿，包括：

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
latest_metrics_json
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

与设计稿相比，当前多了一个已实现字段：

- `latest_metrics_json`

作用：

- 直接保存最近一轮指标，详情页读取更方便

### 6.2 `fl_task_round_metric`

已实现字段：

```text
id
task_id
round_no
loss
primary_metric
metrics_json
created_at
```

当前实现方式：

- Java 通过 Runner 拉取新轮次指标
- 使用 `(task_id, round_no)` 唯一键防止重复插入

## 7. 前端到 Java 的接口

设计中的前端公开接口已经落地，统一由 `FlTaskController` 提供。

当前已实现接口：

- `POST /api/fl-tasks`
- `GET /api/fl-tasks`
- `GET /api/fl-tasks/{taskId}`
- `GET /api/fl-tasks/{taskId}/rounds`
- `POST /api/fl-tasks/{taskId}/start`
- `POST /api/fl-tasks/{taskId}/stop`
- `GET /api/fl-datasets`
- `GET /api/fl-runner/health`

当前统一返回格式：

```json
{
  "code": 200,
  "message": "成功",
  "data": {}
}
```

### 7.1 创建任务

已实现：

- 请求体支持设计稿中的主要参数
- 创建时只落库，不自动启动

实际支持字段：

- `name`
- `taskType`
- `datasetName`
- `datasetPath`
- `datasetFormat`
- `modelSource`
- `numRounds`
- `nodeCount`
- `localEpochs`
- `batchSize`
- `learningRate`
- `fractionEvaluate`

### 7.2 启动任务

已实现：

- 仅允许启动 `CREATED` 状态任务
- 若已有其他任务运行，会直接拒绝启动
- 启动后会立即触发一次同步

### 7.3 停止任务

已实现：

- 仅对 `RUNNING` 任务调用 Runner 停止
- 停止后会同步最新状态

### 7.4 任务列表

已实现：

- 支持 `status` 条件过滤
- 支持 `name` 模糊搜索
- 支持 `page`、`size` 分页
- 返回摘要信息和当前进度

### 7.5 任务详情

已实现：

- 返回任务基础信息
- 返回最新指标
- 返回最终指标
- 返回最终模型路径
- 返回错误信息

当前实现中，若任务仍是 `RUNNING`，查询详情时会先触发一次同步。

### 7.6 查询每轮指标

已实现：

- 从数据库返回当前任务所有轮次指标
- 默认按 `round_no` 正序返回

### 7.7 数据集列表

已实现：

- 前端不再扫描 Java 本机磁盘
- Java 会调用远端 Runner 的 `/runner/datasets`
- 当前会返回 `name`、`path`、`format`

补充实现：

- 新增了 `GET /api/fl-runner/health`
- 用于前端检查训练服务是否在线

## 8. Java 到 Python 执行器的内部接口

设计中的内部接口已基本实现。

当前 Java 通过 `FlowerRunnerClient` 调用这些接口：

- `POST /runner/tasks`
- `GET /runner/tasks/{taskId}`
- `GET /runner/tasks/{taskId}/rounds?afterRound={n}`
- `POST /runner/tasks/{taskId}/stop`
- `GET /runner/datasets`
- `GET /health`

此外，Runner 还保留了兼容接口：

- `GET /status`
- `POST /stop`

### 8.1 启动任务

已实现：

- Java 组装 `taskId`
- Java 传递 `appDir`
- Java 传递 `workDir`
- Java 传递 `runConfig`
- Java 传递 `env`

当前实际传递的 `runConfig` 包括：

- `task-type`
- `num-server-rounds`
- `node-count`
- `local-epochs`
- `learning-rate`
- `batch-size`
- `fraction-evaluate`

当前实际传递的环境变量包括：

- `FLOWER_DETECTION_DATASET`
- `FLOWER_DETECTION_DATASET_FORMAT`
- `FLOWER_YOLO_MODEL`

### 8.2 查询任务状态

已实现：

- 返回任务状态
- 返回当前轮次
- 返回最新指标
- 返回最终指标
- 返回模型路径
- 返回错误信息
- 返回开始结束时间

### 8.3 查询新轮次指标

已实现：

- 支持 `afterRound`
- Java 每次只拉取增量轮次
- 拉取后插入 `fl_task_round_metric`

### 8.4 停止任务

已实现：

- 可按 `taskId` 停止指定任务
- Windows 下使用 `taskkill /T /F`
- 非 Windows 下使用 `terminate/kill`

### 8.5 健康检查

已实现：

- Runner 提供 `/health`
- Java 通过 `/api/fl-runner/health` 转发给前端

## 9. 交互流程

设计中的四条主流程已经跑通。

### 9.1 创建任务

当前流程：

1. 前端调 `POST /api/fl-tasks`
2. Java 校验请求参数
3. Java 生成 `taskId`
4. Java 将任务写入 `fl_task`
5. 返回 `CREATED`

### 9.2 启动任务

当前流程：

1. 前端调 `POST /api/fl-tasks/{taskId}/start`
2. Java 检查任务状态和是否有其他运行中任务
3. Java 调 Runner 的 `POST /runner/tasks`
4. Runner 创建工作目录并启动 Flower 子进程
5. Java 将任务状态更新为 `RUNNING`
6. Java 立即同步一次任务状态

### 9.3 运行中同步

当前流程：

1. Java 定时扫描数据库里 `RUNNING` 的任务
2. Java 调 Runner 的轮次接口拉取增量指标
3. Java 将新轮次写入 `fl_task_round_metric`
4. Java 调 Runner 状态接口同步当前状态
5. Java 更新 `fl_task` 中的轮次、主指标、最终指标、错误信息等

### 9.4 停止任务

当前流程：

1. 前端调 `POST /api/fl-tasks/{taskId}/stop`
2. Java 调 Runner 停止指定任务
3. Runner 结束子进程并刷新状态文件
4. Java 再同步一次状态并更新数据库

## 10. Python 侧需要改的点

设计中列出的 Python 改造点，当前已经大部分落地。

### 10.1 改造 `flower_server_api.py`

已实现：

- 从简单全局进程控制改为任务型 Runner
- 支持按任务创建工作目录
- 支持结构化状态文件
- 支持任务查询
- 支持任务停止
- 支持任务轮次指标查询
- 支持 Runner 健康检查
- 支持远端数据集列表
- 支持 Windows 和 Linux 的进程停止逻辑

当前补充实现：

- 修复了 `_ACTIVE_TASK` 的全局变量作用域问题
- 修复了 Flower `--run-config` 字符串格式问题
- 增加了数据集格式自动识别

### 10.2 改造 `fl/server_app.py`

已实现：

- 启动时更新 `status.json`
- 每轮评估后追加 `round_metrics.jsonl`
- 完成后写 `summary.json`
- 完成后写最终模型文件
- 失败后写错误信息

### 10.3 输出格式建议

设计中的三类结构化输出当前都已落地：

- `status.json`
- `round_metrics.jsonl`
- `summary.json`

另外，Runner 还会维护：

- `task.json`
- `train.log`
- `final_model.pt`

补充实现：

- 检测任务现在支持 `VOC` 和 `YOLO`
- 分类任务仍使用内置 CIFAR-10，不读取外部数据集目录

## 11. 参数设计建议

设计中的核心参数当前已经落地。

前端创建任务当前可传：

- `name`
- `taskType`
- `datasetName`
- `datasetPath`
- `datasetFormat`
- `modelSource`
- `numRounds`
- `nodeCount`
- `localEpochs`
- `batchSize`
- `learningRate`
- `fractionEvaluate`

Java 实际会传给 Runner 的关键参数：

- `task-type`
- `num-server-rounds`
- `node-count`
- `local-epochs`
- `learning-rate`
- `batch-size`
- `fraction-evaluate`
- `federationConfig.options.num-supernodes`

当前配置项：

```yaml
flower:
  runner:
    base-url: http://10.129.45.44:9000
    app-dir: linux_flower_demo
    runs-dir: linux_flower_demo/runs
    datasets-root: linux_flower_demo/allDatasets
    sync-interval-ms: 5000
```

说明：

- `base-url` 指向远端 Python Runner
- 其余路径语义是 Runner 所在机器上的路径语义

## 12. 前端展示建议

设计中建议的前端展示方式，当前已有对应数据支撑。

当前前端已经可以展示：

- 数据集下拉列表
- 任务列表
- 任务状态
- 当前轮次与总轮次
- 进度百分比
- 最近一轮指标
- 最终指标
- 每轮指标折线图数据
- 错误信息

当前单独补了一份前端接口文档：

- `docs/fltask-frontend-api.md`

当前仍建议前端这样做：

- 训练详情页按 5 秒轮询
- 列表页显示摘要
- 详情页显示完整指标与错误信息

## 13. 最小实现顺序

从设计稿提出的最小实现顺序来看，当前完成情况如下：

### 已完成

1. Python Runner 改造成任务型接口
2. `server_app.py` 输出结构化结果
3. Java 新建 `fltask` 模块并接入数据库
4. Java 与远端 Python Runner 联调
5. 删除旧 `/federated/**` 代码
6. 前端接口文档补齐

### 部分完成

1. 检测任务数据集支持：`VOC` 和 `YOLO` 已支持
2. 分类任务保留，但仍不是外部自定义数据集模式

### 未完成

1. 模型文件下载接口
2. 任务队列或并发调度
3. 分类任务自定义数据集支持
4. 更完整的联调和自动化测试

## 14. 一句话结论

设计稿中的“Java 管任务、Python 管进程、Flower 管训练”的最小闭环已经基本实现，并且已经支持前端创建任务、启动训练、轮询状态、查看每轮指标和最终结果。

当前最主要的剩余边界不是架构问题，而是功能细节还没继续扩展，尤其是：

- `classification` 自定义数据集
- 模型文件下载
- 并发任务与调度
