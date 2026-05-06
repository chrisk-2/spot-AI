# Starfleet CMDB Inventory — 20260506-143437

| Host | IP | CPU | RAM | Board | GPU | Ollama | Failed |
|---|---:|---|---:|---|---|---:|---:|
| dns-core | 192.168.60.10 | AMD Ryzen 5 PRO 2400G with Radeon Vega Graphics | 6.7Gi |  |  | inactive | 0 |
| sentinel-core | 192.168.1.3 | None | None |  |  | None | None |
| spot-core | 192.168.60.30 | Intel(R) Core(TM) i7-6700 CPU @ 3.40GHz | 31Gi |  |  | inactive | 0 |
| spot-ui-01 | 192.168.10.12 | 11th Gen Intel(R) Core(TM) i5-1135G7 @ 2.40GHz | 30Gi | Dell Inc. 0H1TR9 |  | inactive | 2 |
| spot-worker-01 | 192.168.10.10 | AMD EPYC 4245P 6-Core Processor | 30Gi |  | 0, NVIDIA GeForce RTX 3060, 12288, 1, 12043, 535.288.01, 39, 16.34, 170.00, 1, 16, 94.06.25.00.80 | active | 1 |
| spot-worker-02 | 192.168.10.11 | Intel(R) Xeon(R) CPU E5-1620 v2 @ 3.70GHz | 31Gi | Dell Inc. 09M8Y8 | 0, Quadro M4000, 8192, 1, 8119, 535.288.01, 44, 12.51, 120.00, 1, 16, 84.04.88.00.06 | 1, NVIDIA GeForce GTX 1060 6GB, 6144, 2, 6070, 535.288.01, 45, 5.81, 120.00, 1, 16, 86.06.63.00.AA | active | 1 |
| spot-worker-03 | 192.168.10.13 | AMD Ryzen 7 2700X Eight-Core Processor | 31Gi |  | 0, NVIDIA GeForce GTX 1070, 8192, 3, 8105, 580.126.09, 35, 8.05, 151.00, 1, 4, 86.04.50.40.1F | 1, NVIDIA GeForce RTX 3060, 12288, 1, 11907, 580.126.09, 36, 15.58, 170.00, 1, 16, 94.06.2F.40.80 | active | 0 |
| spot-worker-04 | 192.168.10.14 | 13th Gen Intel(R) Core(TM) i7-13700KF | 62Gi |  | 0, Quadro P6000, 24576, 3, 24435, 580.126.09, 25, 9.19, 250.00, 1, 16, 86.02.1D.00.01 | active | 0 |
| spot-worker-05 | 192.168.10.15 | Intel(R) Core(TM) i7-8700 CPU @ 3.20GHz | 31Gi | ASUSTeK COMPUTER INC. PRIME Z390-A | 0, Quadro P6000, 23040, 0, 22910, 535.288.01, 36, 55.29, 250.00, 3, 16, 86.02.2D.00.04 | active | 0 |
| starfleet-core | 192.168.60.20 | Intel(R) Core(TM) i5-7500T CPU @ 2.70GHz | 7.6Gi |  |  | inactive | 0 |
| starfleet-tower | 192.168.30.5 | Intel(R) Core(TM) i5-3427U CPU @ 1.80GHz | 7.6Gi |  |  | inactive | 0 |

## Artifacts
- JSON: `fleet-cmdb-20260506-143437.json`
- CSV: `fleet-cmdb-20260506-143437.csv`
- Raw per-host captures: `raw/`
- Per-host normalized JSON: `json/`

## Safety
- Read-only inventory collection.
- No file writes on workers.
- No service restarts.
- No package installs.
