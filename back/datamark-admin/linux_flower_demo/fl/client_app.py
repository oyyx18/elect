"""Flower ClientApp entry point."""

from __future__ import annotations

import torch
from flwr.app import ArrayRecord, Context, Message, MetricRecord, RecordDict
from flwr.clientapp import ClientApp

from fl.task import get_task

app = ClientApp()


@app.train()
def train(msg: Message, context: Context):
    """Train the model on local data."""

    task = get_task(context.run_config.get("task-type"))

    model = task.Net()
    model.load_state_dict(msg.content["arrays"].to_torch_state_dict())
    device = torch.device("cuda:0" if torch.cuda.is_available() else "cpu")
    model.to(device)

    partition_id = context.node_config["partition-id"]
    num_partitions = context.node_config["num-partitions"]
    batch_size = context.run_config["batch-size"]
    trainloader, _ = task.load_data(partition_id, num_partitions, batch_size)

    train_loss, train_metrics = task.train(
        model,
        trainloader,
        context.run_config["local-epochs"],
        msg.content["config"]["lr"],
        device,
    )

    model_record = ArrayRecord(model.state_dict())
    metrics = dict(train_metrics)
    metrics["train_loss"] = train_loss
    metrics["num-examples"] = len(trainloader.dataset)
    metric_record = MetricRecord(metrics)
    content = RecordDict({"arrays": model_record, "metrics": metric_record})
    return Message(content=content, reply_to=msg)


@app.evaluate()
def evaluate(msg: Message, context: Context):
    """Evaluate the model on local data."""

    task = get_task(context.run_config.get("task-type"))

    model = task.Net()
    model.load_state_dict(msg.content["arrays"].to_torch_state_dict())
    device = torch.device("cuda:0" if torch.cuda.is_available() else "cpu")
    model.to(device)

    partition_id = context.node_config["partition-id"]
    num_partitions = context.node_config["num-partitions"]
    batch_size = context.run_config["batch-size"]
    _, valloader = task.load_data(partition_id, num_partitions, batch_size)

    eval_loss, eval_metrics = task.test(
        model,
        valloader,
        device,
    )

    metrics = dict(eval_metrics)
    metrics["eval_loss"] = eval_loss
    metrics["num-examples"] = len(valloader.dataset)
    metric_record = MetricRecord(metrics)
    content = RecordDict({"metrics": metric_record})
    return Message(content=content, reply_to=msg)
