"""Flower ServerApp entry point."""

from __future__ import annotations

import torch
from flwr.app import ArrayRecord, ConfigRecord, Context, MetricRecord
from flwr.serverapp import Grid, ServerApp
from flwr.serverapp.strategy import FedAvg

from fl.task import get_task

app = ServerApp()
TASK_MODULE = None


@app.main()
def main(grid: Grid, context: Context) -> None:
    """Main entry point for the ServerApp."""

    global TASK_MODULE

    fraction_evaluate: float = context.run_config["fraction-evaluate"]
    num_rounds: int = context.run_config["num-server-rounds"]
    lr: float = context.run_config["learning-rate"]
    TASK_MODULE = get_task(context.run_config.get("task-type"))

    global_model = TASK_MODULE.Net()
    arrays = ArrayRecord(global_model.state_dict())

    strategy = FedAvg(fraction_evaluate=fraction_evaluate)

    result = strategy.start(
        grid=grid,
        initial_arrays=arrays,
        train_config=ConfigRecord({"lr": lr}),
        num_rounds=num_rounds,
        evaluate_fn=global_evaluate,
    )

    print("\nSaving final model to disk...")
    state_dict = result.arrays.to_torch_state_dict()
    torch.save(state_dict, "final_model.pt")


def global_evaluate(server_round: int, arrays: ArrayRecord) -> MetricRecord:
    """Evaluate model on central data."""

    global TASK_MODULE
    if TASK_MODULE is None:
        TASK_MODULE = get_task()

    model = TASK_MODULE.Net()
    model.load_state_dict(arrays.to_torch_state_dict())
    device = torch.device("cuda:0" if torch.cuda.is_available() else "cpu")
    model.to(device)

    test_dataloader = TASK_MODULE.load_centralized_dataset()
    test_loss, test_metrics = TASK_MODULE.test(model, test_dataloader, device)

    if isinstance(test_metrics, (dict, MetricRecord)):
        metrics = dict(test_metrics)
    else:
        metric_name = getattr(TASK_MODULE, "METRIC_NAME", "metric")
        metrics = {metric_name: float(test_metrics)}

    metrics["loss"] = float(test_loss)
    return MetricRecord(metrics)
