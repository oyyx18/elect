"""Image classification task (CIFAR-10, ResNet18)."""

from __future__ import annotations

import torch
import torch.nn as nn
import torchvision
from datasets import ClassLabel, Dataset, Features, Image
from flwr_datasets.partitioner import IidPartitioner
from torch.utils.data import DataLoader
from torchvision.transforms import Compose, Normalize, ToTensor

pytorch_transforms = Compose(
    [
        ToTensor(),
        Normalize((0.5, 0.5, 0.5), (0.5, 0.5, 0.5)),
    ]
)

local_cifar10_dataset: Dataset | None = None


class Net(nn.Module):
    """CIFAR-10 classifier based on ResNet18 (adapted for 32x32 inputs)."""

    def __init__(self) -> None:
        super().__init__()
        self.model = torchvision.models.resnet18(weights=None)
        self.model.conv1 = nn.Conv2d(3, 64, kernel_size=3, stride=1, padding=1, bias=False)
        self.model.maxpool = nn.Identity()
        self.model.fc = nn.Linear(self.model.fc.in_features, 10)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.model(x)


def apply_transforms(batch: dict) -> dict:
    """Apply PyTorch transforms to a Hugging Face Dataset batch."""

    batch["img"] = [pytorch_transforms(img) for img in batch["img"]]
    return batch


def load_local_cifar10_dataset() -> Dataset:
    """Load CIFAR-10 locally and convert it to a Hugging Face Dataset."""

    global local_cifar10_dataset

    if local_cifar10_dataset is None:
        print("Loading local CIFAR10 dataset...")

        trainset = torchvision.datasets.CIFAR10(
            root="./data",
            train=True,
            download=True,
            transform=None,
        )

        dataset_train_dict = {"img": [], "label": []}
        for img, label in trainset:
            dataset_train_dict["img"].append(img)
            dataset_train_dict["label"].append(label)

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

        local_cifar10_dataset = Dataset.from_dict(
            dataset_train_dict,
            features=features,
            split="train",
        )

        print(f"Loaded local CIFAR10 dataset with {len(local_cifar10_dataset)} samples")

    return local_cifar10_dataset


def load_data(partition_id: int, num_partitions: int, batch_size: int):
    """Load a partition of CIFAR-10 and return train/test dataloaders."""

    hf_train_dataset = load_local_cifar10_dataset()

    partitioner = IidPartitioner(num_partitions=num_partitions)
    partitioner.dataset = hf_train_dataset
    partition = partitioner.load_partition(partition_id)

    partition_train_test = partition.train_test_split(test_size=0.2, seed=42)
    partition_train_test = partition_train_test.with_transform(apply_transforms)

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
    """Load CIFAR-10 test set for centralized evaluation."""

    testset = torchvision.datasets.CIFAR10(
        root="./data",
        train=False,
        download=True,
        transform=None,
    )

    dataset_test_dict = {"img": [], "label": []}
    for img, label in testset:
        dataset_test_dict["img"].append(img)
        dataset_test_dict["label"].append(label)

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

    hf_test_dataset = Dataset.from_dict(
        dataset_test_dict,
        features=features,
        split="test",
    )
    hf_test_dataset = hf_test_dataset.with_transform(apply_transforms)

    return DataLoader(hf_test_dataset, batch_size=128)


def train(net: nn.Module, trainloader: DataLoader, epochs: int, lr: float, device: torch.device):
    """Train the model locally and return (loss, metrics)."""

    net.to(device)
    criterion = torch.nn.CrossEntropyLoss().to(device)
    optimizer = torch.optim.SGD(net.parameters(), lr=lr, momentum=0.9)
    net.train()

    running_loss = 0.0
    for _ in range(epochs):
        for batch in trainloader:
            images = batch["img"].to(device)
            labels = batch["label"].to(device)

            optimizer.zero_grad()
            loss = criterion(net(images), labels)
            loss.backward()
            optimizer.step()

            running_loss += loss.item()

    avg_trainloss = running_loss / len(trainloader)
    return avg_trainloss, {}


def test(net: nn.Module, testloader: DataLoader, device: torch.device):
    """Evaluate the model and return (loss, metrics)."""

    net.to(device)
    criterion = torch.nn.CrossEntropyLoss()

    correct = 0
    loss = 0.0
    with torch.no_grad():
        for batch in testloader:
            images = batch["img"].to(device)
            labels = batch["label"].to(device)

            outputs = net(images)
            loss += criterion(outputs, labels).item()
            correct += (torch.max(outputs.data, 1)[1] == labels).sum().item()

    accuracy = correct / len(testloader.dataset)
    loss = loss / len(testloader)
    return loss, {"accuracy": accuracy}


def check_local_dataset() -> None:
    """Debug helper to inspect dataset features and a sample."""

    dataset = load_local_cifar10_dataset()
    print(f"Dataset features: {dataset.features}")
    print(f"First sample: {dataset[0]}")
    print(f"Dataset size: {len(dataset)}")


if __name__ == "__main__":
    check_local_dataset()
