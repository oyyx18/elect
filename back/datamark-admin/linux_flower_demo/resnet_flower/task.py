"""pytorchexample: A Flower / PyTorch app.

本模块负责：
1) 定义一个轻量级 ResNet 模型（用于 CIFAR-10 分类）。
2) 将本地 CIFAR-10 数据集转换为 Hugging Face Dataset，并按需分区。
3) 提供训练与评估函数，供联邦学习或集中式流程调用。
"""

from __future__ import annotations

import torch
import torch.nn as nn
import torchvision
from datasets import Dataset
from flwr_datasets.partitioner import IidPartitioner
from torch.utils.data import DataLoader
from torchvision.transforms import Compose, Normalize, ToTensor

# 注意：使用 Hugging Face Dataset 的 with_transform 机制时，batch["img"]
# 仍然是 PIL 图像对象；这里统一设置 PyTorch 侧的预处理流程。
pytorch_transforms = Compose(
    [
        ToTensor(),  # PIL -> torch.Tensor，范围从 [0, 255] 归一化到 [0.0, 1.0]
        Normalize((0.5, 0.5, 0.5), (0.5, 0.5, 0.5)),  # 逐通道归一化到近似 [-1, 1]
    ]
)

# 全局缓存：避免每次调用都重复下载/读取 CIFAR-10。
local_cifar10_dataset = None


class Net(nn.Module):
    """CIFAR-10 classifier based on ResNet18 (adapted for 32x32 inputs)."""

    def __init__(self) -> None:
        super(Net, self).__init__()
        self.model = torchvision.models.resnet18(weights=None)
        # Use a 3x3 conv and remove maxpool for small inputs.
        self.model.conv1 = nn.Conv2d(3, 64, kernel_size=3, stride=1, padding=1, bias=False)
        self.model.maxpool = nn.Identity()
        self.model.fc = nn.Linear(self.model.fc.in_features, 10)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.model(x)


def apply_transforms(batch: dict) -> dict:
    """对 Hugging Face Dataset 的 batch 应用 PyTorch 预处理。"""
    # batch["img"] 是一个 PIL 图像列表，这里逐张转换为 tensor 并归一化。
    batch["img"] = [pytorch_transforms(img) for img in batch["img"]]
    return batch


def load_local_cifar10_dataset() -> Dataset:
    """加载本地 CIFAR-10 数据集，并转换为 Hugging Face Dataset。"""
    global local_cifar10_dataset

    # 仅在首次调用时下载与转换，后续直接使用缓存。
    if local_cifar10_dataset is None:
        print("Loading local CIFAR10 dataset...")

        # 下载 CIFAR-10 训练集（PyTorch 格式）。
        # transform=None，避免 PyTorch 数据集提前转换；后续统一应用 with_transform。
        trainset = torchvision.datasets.CIFAR10(
            root="./data",
            train=True,
            download=True,
            transform=None,
        )

        # 将 PyTorch Dataset 转为字典结构，便于构建 Hugging Face Dataset。
        dataset_train_dict = {"img": [], "label": []}
        for img, label in trainset:
            dataset_train_dict["img"].append(img)
            dataset_train_dict["label"].append(label)

        # 定义 Dataset 的特征：图像 + 类别（含 10 个类别名称）。
        from datasets import ClassLabel, Features, Image

        features = Features(
            {
                "img": Image(decode=True, id=None),
                "label": ClassLabel(
                    names=[
                        "airplane",
                        "automobile",
                        "bird",
                        "cat",
                        "deer",
                        "dog",
                        "frog",
                        "horse",
                        "ship",
                        "truck",
                    ]
                ),
            }
        )

        # 创建 Hugging Face Dataset（标记为 train split）。
        local_cifar10_dataset = Dataset.from_dict(
            dataset_train_dict,
            features=features,
            split="train",
        )

        print(f"Loaded local CIFAR10 dataset with {len(local_cifar10_dataset)} samples")

    return local_cifar10_dataset


def load_data(partition_id: int, num_partitions: int, batch_size: int):
    """加载指定分区的 CIFAR-10 数据，并返回训练/测试 DataLoader。"""
    # 先读取本地训练集（Hugging Face Dataset）。
    hf_train_dataset = load_local_cifar10_dataset()

    # 使用 IID 分区器，将数据均匀划分为 num_partitions 份。
    partitioner = IidPartitioner(num_partitions=num_partitions)
    partitioner.dataset = hf_train_dataset

    # 取出指定分区（partition_id）。
    partition = partitioner.load_partition(partition_id)

    # 将该分区再切分为训练集/测试集（80%/20%）。
    partition_train_test = partition.train_test_split(test_size=0.2, seed=42)

    # 应用统一的图像预处理（ToTensor + Normalize）。
    partition_train_test = partition_train_test.with_transform(apply_transforms)

    # 构建 DataLoader：训练集需要 shuffle，测试集不需要。
    trainloader = DataLoader(
        partition_train_test["train"],
        batch_size=batch_size,
        shuffle=True,
    )
    testloader = DataLoader(
        partition_train_test["test"],
        batch_size=batch_size,
    )

    return trainloader, testloader


def load_centralized_dataset() -> DataLoader:
    """加载本地测试集（集中式评估用），返回 DataLoader。"""
    # 下载 CIFAR-10 测试集（PyTorch 格式）。
    testset = torchvision.datasets.CIFAR10(
        root="./data",
        train=False,
        download=True,
        transform=None,
    )

    # 将测试集转换为 Hugging Face Dataset 所需的字典格式。
    dataset_test_dict = {"img": [], "label": []}
    for img, label in testset:
        dataset_test_dict["img"].append(img)
        dataset_test_dict["label"].append(label)

    # 定义特征 schema（与训练集一致）。
    from datasets import ClassLabel, Features, Image

    features = Features(
        {
            "img": Image(decode=True, id=None),
            "label": ClassLabel(
                names=[
                    "airplane",
                    "automobile",
                    "bird",
                    "cat",
                    "deer",
                    "dog",
                    "frog",
                    "horse",
                    "ship",
                    "truck",
                ]
            ),
        }
    )

    # 构建 Hugging Face Dataset，并标记为 test split。
    hf_test_dataset = Dataset.from_dict(
        dataset_test_dict,
        features=features,
        split="test",
    )

    # 应用图像预处理。
    hf_test_dataset = hf_test_dataset.with_transform(apply_transforms)

    # 返回测试集 DataLoader（batch_size 固定为 128）。
    return DataLoader(hf_test_dataset, batch_size=128)


def train(net: nn.Module, trainloader: DataLoader, epochs: int, lr: float, device: torch.device):
    """在本地训练模型，返回平均训练损失。"""
    # 将模型移动到目标设备（CPU 或 GPU）。
    net.to(device)
    # 交叉熵损失用于多分类任务。
    criterion = torch.nn.CrossEntropyLoss().to(device)
    # SGD 优化器，学习率由服务器下发或配置指定。
    optimizer = torch.optim.SGD(net.parameters(), lr=lr, momentum=0.9)
    # 训练模式：启用训练态的层行为（如 Dropout/BN）。
    net.train()

    running_loss = 0.0
    for _ in range(epochs):
        for batch in trainloader:
            # 取出图像与标签，并移动到目标设备。
            images = batch["img"].to(device)
            labels = batch["label"].to(device)

            # 清空梯度，避免累积。
            optimizer.zero_grad()
            # 前向传播、计算损失、反向传播、参数更新。
            loss = criterion(net(images), labels)
            loss.backward()
            optimizer.step()

            running_loss += loss.item()

    # 用 batch 数求平均，得到训练损失指标。
    avg_trainloss = running_loss / len(trainloader)
    return avg_trainloss


def test(net: nn.Module, testloader: DataLoader, device: torch.device):
    """在测试集上评估模型，返回 (loss, accuracy)。"""
    # 切换为评估模式。
    net.to(device)
    criterion = torch.nn.CrossEntropyLoss()

    correct = 0
    loss = 0.0
    with torch.no_grad():
        for batch in testloader:
            # 取出图像与标签，并移动到目标设备。
            images = batch["img"].to(device)
            labels = batch["label"].to(device)

            # 前向推理得到 logits。
            outputs = net(images)
            # 累积损失。
            loss += criterion(outputs, labels).item()
            # 统计预测正确的样本数。
            correct += (torch.max(outputs.data, 1)[1] == labels).sum().item()

    # accuracy = 正确数 / 总样本数
    accuracy = correct / len(testloader.dataset)
    # 平均 loss = loss 总和 / batch 数
    loss = loss / len(testloader)
    return loss, accuracy


def check_local_dataset() -> None:
    """调试用：打印数据集特征与首条样本，检查加载是否正常。"""
    dataset = load_local_cifar10_dataset()
    print(f"Dataset features: {dataset.features}")
    print(f"First sample: {dataset[0]}")
    print(f"Dataset size: {len(dataset)}")


if __name__ == "__main__":
    # 直接运行该文件时，做一次数据集加载自检。
    check_local_dataset()
