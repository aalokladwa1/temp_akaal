"""
akaalEngine.discovery.strategies.application
===============================================
SaaS/application-platform discovery strategies (Salesforce, ServiceNow, SAP
Application Ecosystem).
"""

from akaalEngine.discovery.strategies.application.salesforce import SalesforceDiscoveryStrategy
from akaalEngine.discovery.strategies.application.servicenow import ServiceNowDiscoveryStrategy
from akaalEngine.discovery.strategies.application.sap_application import SAPApplicationDiscoveryStrategy

__all__ = [
    "SalesforceDiscoveryStrategy",
    "ServiceNowDiscoveryStrategy",
    "SAPApplicationDiscoveryStrategy",
]
