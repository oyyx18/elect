"""pytorchexample: A Flower / PyTorch app.

该文件定义联邦学习服务器端逻辑：
- 初始化全局模型与 FedAvg 策略
- 控制联邦轮次、下发训练超参
- 在每轮（或指定轮次）进行集中式评估
"""

import torch
from flwr.app import ArrayRecord, ConfigRecord, Context, MetricRecord
from flwr.serverapp import Grid, ServerApp
from flwr.serverapp.strategy import FedAvg

from pytorchexample.task import Net, load_centralized_dataset, test

# Create ServerApp：提供服务器端主入口
app = ServerApp()


@app.main()
def main(grid: Grid, context: Context) -> None:
    """Main entry point for the ServerApp."""

    # 1) 读取运行配置（来自 CLI/配置文件）
    fraction_evaluate: float = context.run_config["fraction-evaluate"]
    num_rounds: int = context.run_config["num-server-rounds"]
    lr: float = context.run_config["learning-rate"]

    # 2) 初始化全局模型权重（作为联邦训练的初始参数）
    global_model = Net()
    arrays = ArrayRecord(global_model.state_dict())

    # 3) 初始化 FedAvg 策略（可扩展为带自定义聚合逻辑）
    strategy = FedAvg(fraction_evaluate=fraction_evaluate)

    # 4) 启动训练流程，运行 num_rounds 轮联邦训练
    result = strategy.start(
        grid=grid,
        initial_arrays=arrays,
        # 下发到客户端的训练超参（如学习率）
        train_config=ConfigRecord({"lr": lr}),
        num_rounds=num_rounds,
        # 服务器端集中式评估函数
        evaluate_fn=global_evaluate,
    )

    # 5) 保存最终聚合后的模型权重
    print("\nSaving final model to disk...")
    state_dict = result.arrays.to_torch_state_dict()
    torch.save(state_dict, "final_model.pt")


def global_evaluate(server_round: int, arrays: ArrayRecord) -> MetricRecord:
    """Evaluate model on central data."""

    # 1) 构建模型并加载当前全局权重
    model = Net()
    model.load_state_dict(arrays.to_torch_state_dict())
    # 优先使用 GPU（如果可用）
    device = torch.device("cuda:0" if torch.cuda.is_available() else "cpu")
    model.to(device)

    # 2) 加载完整测试集（集中式评估）
    test_dataloader = load_centralized_dataset()

    # 3) 计算损失与准确率
    test_loss, test_acc = test(model, test_dataloader, device)

    # 4) 返回指标给 Flower 服务器
    return MetricRecord({"accuracy": test_acc, "loss": test_loss})
