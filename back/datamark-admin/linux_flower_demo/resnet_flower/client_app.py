"""pytorchexample: A Flower / PyTorch app.

该文件定义 Flower 的 ClientApp 逻辑：
- 训练入口：从服务器收到模型权重与超参，加载本地数据并训练，然后回传更新后的权重与指标
- 评估入口：从服务器收到模型权重，加载本地验证集并评估，然后回传指标
"""

import torch
from flwr.app import ArrayRecord, Context, Message, MetricRecord, RecordDict
from flwr.clientapp import ClientApp

from pytorchexample.task import Net, load_data
from pytorchexample.task import test as test_fn
from pytorchexample.task import train as train_fn

# Flower ClientApp：提供训练与评估的入口装饰器
app = ClientApp()


@app.train()
def train(msg: Message, context: Context):
    """Train the model on local data."""
    # 1) 构建模型并加载服务器下发的全局权重
    model = Net()
    model.load_state_dict(msg.content["arrays"].to_torch_state_dict())
    # 选择计算设备：优先使用 GPU（如果可用）
    device = torch.device("cuda:0" if torch.cuda.is_available() else "cpu")
    model.to(device)

    # 2) 根据当前节点的配置获取该客户端的数据分区
    partition_id = context.node_config["partition-id"]
    num_partitions = context.node_config["num-partitions"]
    batch_size = context.run_config["batch-size"]
    trainloader, _ = load_data(partition_id, num_partitions, batch_size)

    # 3) 进行本地训练，返回平均训练损失
    train_loss = train_fn(
        model,
        trainloader,
        context.run_config["local-epochs"],
        msg.content["config"]["lr"],
        device,
    )

    # 4) 打包并返回训练结果
    # arrays：模型权重（用于服务器聚合）
    # metrics：训练损失与样本数（用于日志与加权）
    model_record = ArrayRecord(model.state_dict())
    metrics = {
        "train_loss": train_loss,
        "num-examples": len(trainloader.dataset),
    }
    metric_record = MetricRecord(metrics)
    content = RecordDict({"arrays": model_record, "metrics": metric_record})
    return Message(content=content, reply_to=msg)


@app.evaluate()
def evaluate(msg: Message, context: Context):
    """Evaluate the model on local data."""
    # 1) 构建模型并加载服务器下发的全局权重
    model = Net()
    model.load_state_dict(msg.content["arrays"].to_torch_state_dict())
    # 选择计算设备：优先使用 GPU（如果可用）
    device = torch.device("cuda:0" if torch.cuda.is_available() else "cpu")
    model.to(device)

    # 2) 获取该客户端的验证集（同一分区的测试子集）
    partition_id = context.node_config["partition-id"]
    num_partitions = context.node_config["num-partitions"]
    batch_size = context.run_config["batch-size"]
    _, valloader = load_data(partition_id, num_partitions, batch_size)

    # 3) 评估模型，得到损失与准确率
    eval_loss, eval_acc = test_fn(
        model,
        valloader,
        device,
    )

    # 4) 打包并返回评估指标
    metrics = {
        "eval_loss": eval_loss,
        "eval_acc": eval_acc,
        "num-examples": len(valloader.dataset),
    }
    metric_record = MetricRecord(metrics)
    content = RecordDict({"metrics": metric_record})
    return Message(content=content, reply_to=msg)
