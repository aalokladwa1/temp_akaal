"""
akaalEngine.telemetry.exporters.prometheus
===========================================
PrometheusTextExporter generating standard Prometheus text exposition format from actual registered metrics.
"""

from typing import List

from akaalEngine.telemetry.metrics.registry import MetricsRegistry


class PrometheusTextExporter:
    """
    Generates standard Prometheus text exposition format.
    """

    def __init__(self, registry: MetricsRegistry) -> None:
        self.registry = registry

    def export_text(self) -> str:
        snapshot = self.registry.get_snapshot()
        lines: List[str] = []

        # Export Counters
        for key, val in snapshot.counters.items():
            metric_name = key.split("{")[0]
            lines.append(f"# TYPE {metric_name} counter")
            lines.append(f"{key} {val}")

        # Export Gauges
        for key, val in snapshot.gauges.items():
            metric_name = key.split("{")[0]
            lines.append(f"# TYPE {metric_name} gauge")
            lines.append(f"{key} {val}")

        # Export Histograms
        for key, metrics_dict in snapshot.histograms.items():
            metric_name = key.split("{")[0]
            lines.append(f"# TYPE {metric_name} summary")
            for sub_name, val in metrics_dict.items():
                lines.append(f'{metric_name}_{sub_name} {val}')

        # Export Timers
        for key, metrics_dict in snapshot.rate_timers.items():
            metric_name = key.split("{")[0]
            lines.append(f"# TYPE {metric_name} summary")
            for sub_name, val in metrics_dict.items():
                lines.append(f'{metric_name}_{sub_name} {val}')

        return "\n".join(lines) + "\n"
