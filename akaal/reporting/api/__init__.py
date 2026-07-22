"""
Reporting API package initialization.
"""

from akaal.reporting.api.client import ReportingClient
from akaal.reporting.api.facade import IPlatform8Facade, Platform8Facade

__all__ = ["ReportingClient", "IPlatform8Facade", "Platform8Facade"]
