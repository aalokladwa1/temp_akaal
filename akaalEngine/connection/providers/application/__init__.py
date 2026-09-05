"""
akaalEngine.connection.providers.application
==============================================
SaaS/application-platform provider strategies (Salesforce, ServiceNow, SAP Application
Ecosystem) -- REST-API-based (and, for SAP, capability-driven RFC/BAPI/IDoc/OData)
connectors that are NOT SQL databases and are not modeled as such.
"""

from akaalEngine.connection.providers.application.salesforce import SalesforceProviderStrategy
from akaalEngine.connection.providers.application.servicenow import ServiceNowProviderStrategy
from akaalEngine.connection.providers.application.sap_application import SAPApplicationProviderStrategy

__all__ = [
    "SalesforceProviderStrategy",
    "ServiceNowProviderStrategy",
    "SAPApplicationProviderStrategy",
]
