# Akaal Migration Engine — Benchmark Capture Sheet

Use this blank benchmark sheet to capture performance metrics and profiles during migration runs to establish base and optimized performance metrics.

---

## Benchmark Capture Metrics

| Metric | Captured Value | Target/Base Value | Notes |
| :--- | :--- | :--- | :--- |
| **Migration Duration** | `[       ] sec` | *Baseline* | Total wall-clock time of the run |
| **Average Throughput (Rows/sec)** | `[       ] rows/s`| *Baseline* | Calculated as total rows / duration |
| **Data Throughput (MB/sec)** | `[       ] MB/s` | *Baseline* | Megabytes of data copied per second |
| **Peak Memory Footprint**| `[       ] MB` | *< 500 MB* | Peak RAM usage during peak transfers |
| **Average Memory Footprint**| `[       ] MB` | *Baseline* | Average RAM consumption |
| **Peak CPU Load** | `[       ] %` | *Baseline* | Highest CPU usage recorded |
| **Average CPU Load** | `[       ] %` | *Baseline* | Average CPU usage across the run |
| **Connection Count** | `[       ]` | *Baseline* | Number of concurrent connections used |
| **Checkpoint Count** | `[       ]` | *Baseline* | Number of SQLite checkpoint writes |
| **Retry Count** | `[       ]` | *0* | Total retry attempts triggered |
| **Failures Encountered** | `[       ]` | *0* | Count of errors causing aborts |

---

## Hardware Environment
* **CPU Model**: `[                     ]`
* **Number of Cores**: `[                     ]`
* **Total Installed RAM (GB)**: `[                     ]`
* **Storage Type (e.g. NVMe, SATA SSD)**: `[                     ]`
* **Network Configuration (e.g. Local Loopback)**: `[                     ]`
