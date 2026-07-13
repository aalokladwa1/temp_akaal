# -*- coding: utf-8 -*-
"""akaal.metrics.exporter

Abstract base class for metrics exporters.
Concrete exporters (e.g., JSON, Prometheus) will implement the ``export``
method, which receives an immutable :class:`MetricsSnapshot`.
"""

from __future__ import annotations

import abc
from typing import Protocol

from .summary import MetricsSnapshot


class MetricsExporter(abc.ABC):
    """Base class for all metrics exporters.

    Subclasses must implement :meth:`export` which processes a
    :class:`MetricsSnapshot`. The method may write to files, send over the
    network, or integrate with monitoring systems – the interface is kept
    deliberately minimal to avoid coupling.
    """

    @abc.abstractmethod
    def export(self, snapshot: MetricsSnapshot) -> None:
        """Export the provided *snapshot*.

        Implementations should not modify the snapshot – it is immutable.
        """
        raise NotImplementedError

# End of exporter.py
