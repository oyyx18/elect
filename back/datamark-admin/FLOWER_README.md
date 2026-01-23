# Flower Federated Learning (Flower 1.24.0, PyTorch App)

## Architecture
- Java backend: orchestrates remote Flower runs via HTTP control API.
- Flower app (Python): uses ClientApp/ServerApp with local simulation (10 nodes).

## Installation
```bash
pip install -r requirements.txt
pip install -e flower_app
```

## Configuration
Add to `application.yml`:
```yaml
flower:
  server:
    remote:
      base-url: http://10.129.45.44:9000
    port: 8080
```

## Usage
1) On the Flower server host (10.129.45.44), start the control API:
```bash
pip install -r requirements.txt
pip install -e flower_app
python3 flower_server_api.py --host 0.0.0.0 --port 9000 --python-exec python3 --app-dir flower_app
```

2) Start the Java backend:
```bash
mvn spring-boot:run
```

3) The Java backend uses its REST endpoints for job creation, start/stop, and monitoring; it will call the remote control API to launch `flwr run` locally on the Flower host.

Note: this flow uses Flower's local simulation with 10 nodes (no external clients required).

## Notes
- CIFAR-10 is partitioned with Flower Datasets `IidPartitioner` (default 10 partitions).
- The local simulation size is defined by `options.num-supernodes` in `flower_app/pyproject.toml`.
- In simulation mode, gRPC ports are not used; the `port` argument from the backend is ignored.

## Flower App Layout
```
flower_app
├── pyproject.toml
└── pytorchexample
    ├── __init__.py
    ├── client_app.py
    ├── server_app.py
    └── task.py
```

## How it Works
- Dataset: CIFAR-10 via Flower Datasets with `IidPartitioner`, 10 partitions.
- ClientApp: trains and evaluates using local partition data; converts `ArrayRecord` to/from `state_dict`.
- ServerApp: runs FedAvg and saves `final_model.pt` after training.
- Control API: receives start/stop from the Java backend and runs `flwr run flower_app`.

## Run locally (without Java backend)
```bash
pip install -e flower_app
flwr run flower_app
```
