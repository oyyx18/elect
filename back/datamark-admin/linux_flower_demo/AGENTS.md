# linux_flower_demo 部署说明（Agent 参考）

> 目标：帮助在 Linux 环境中部署并运行 `linux_flower_demo` 联邦学习示例（Flower + PyTorch），支持分类与检测两类任务。

## 项目概览
- 框架：Flower (`flwr`) + PyTorch
- 入口：`fl.server_app:app`（服务端）与 `fl.client_app:app`（客户端）
- 默认任务：检测（`task-type = "detection"`，见 `pyproject.toml`）
- 输出：训练完成后在工作目录生成 `final_model.pt`

## 目录结构要点
- `fl/`：Flower 的 server/client app 与任务实现
  - `fl/server_app.py`：联邦训练主流程
  - `fl/client_app.py`：客户端训练与评估
  - `fl/task.py`：任务路由（分类/检测）
  - `fl/task_classification.py`：CIFAR-10 分类
  - `fl/task_detection.py`：YOLO 格式目标检测
- `allDatasets/`：本地数据示例（可供整理使用）
- `tools/`：数据处理与标注辅助脚本


## 任务切换（分类 / 检测）
- 通过运行配置指定：
```bash
# 切换到分类任务
flwr run . --run-config "task-type=classification"
```

- `fl/task.py` 还支持环境变量：
  - `FLOWER_TASK_TYPE=classification|detection|yolo|cls`

> 说明：Server/Client 优先使用 `run-config` 的 `task-type`，未提供时才使用环境变量。

## 目标检测数据要求（YOLO 格式）
`fl/task_detection.py` 期望数据结构：
```
<DATASET_ROOT>/
  images/
    train/  (*.jpg|png|...)
    val/
  labels/
    train/  (*.txt)
    val/
```
- 通过环境变量指定：
```bash
export YOLO_DATASET_ROOT=/abs/path/to/dataset
```

> 注意：`allDatasets/` 下的样例数据需要整理为上述目录结构后再使用。

## 训练过程说明
- 服务端使用 `FedAvg` 聚合参数（见 `fl/server_app.py`）
- 客户端在本地分区数据上训练（`partition-id` / `num-partitions` 由 Flower 注入）
- 每轮训练后：Server 触发全局评估并最终保存 `final_model.pt`

