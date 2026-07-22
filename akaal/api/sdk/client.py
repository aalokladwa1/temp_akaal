"""
Main Entry Point for typed Python SDK (AkaalClient & AsyncAkaalClient).
"""

import asyncio
from akaal.api.sdk.modules.jobs import JobApi
from akaal.api.sdk.modules.workflows import WorkflowApi
from akaal.api.sdk.modules.schema import SchemaApi
from akaal.api.sdk.modules.reporting import ReportingApi
from akaal.api.sdk.modules.monitoring import MonitoringApi


class AsyncAkaalClient:
    """Asynchronous Python SDK Client for AKAAL Platform 7."""

    def __init__(self, api_key: str = None, endpoint: str = "http://localhost:8000") -> None:
        self.api_key = api_key
        self.endpoint = endpoint
        self.jobs = JobApi()
        self.workflows = WorkflowApi()
        self.schema = SchemaApi()
        self.reporting = ReportingApi()
        self.monitoring = MonitoringApi()


class AkaalClient:
    """Synchronous Python SDK Client for AKAAL Platform 7."""

    def __init__(self, api_key: str = None, endpoint: str = "http://localhost:8000") -> None:
        self._async_client = AsyncAkaalClient(api_key=api_key, endpoint=endpoint)
        self.jobs = _SyncJobWrapper(self._async_client.jobs)
        self.workflows = _SyncWorkflowWrapper(self._async_client.workflows)
        self.schema = _SyncSchemaWrapper(self._async_client.schema)
        self.reporting = _SyncReportingWrapper(self._async_client.reporting)
        self.monitoring = _SyncMonitoringWrapper(self._async_client.monitoring)


class _SyncJobWrapper:
    def __init__(self, async_job_api: JobApi) -> None:
        self._api = async_job_api

    def submit(self, job_type: str, payload: dict, priority: int = 5):
        return asyncio.run(self._api.submit(job_type, payload, priority))

    def get_status(self, job_id: str):
        return asyncio.run(self._api.get_status(job_id))

    def cancel(self, job_id: str, reason: str = "User cancelled"):
        return asyncio.run(self._api.cancel(job_id, reason=reason))


class _SyncWorkflowWrapper:
    def __init__(self, async_api: WorkflowApi) -> None:
        self._api = async_api

    def execute(self, workflow_id: str, steps: list, parameters: dict = None):
        return asyncio.run(self._api.execute(workflow_id, steps, parameters=parameters))


class _SyncSchemaWrapper:
    def __init__(self, async_api: SchemaApi) -> None:
        self._api = async_api

    def check_compatibility(self, schema_name: str, ddl: str):
        return asyncio.run(self._api.check_compatibility(schema_name, ddl))


class _SyncReportingWrapper:
    def __init__(self, async_api: ReportingApi) -> None:
        self._api = async_api

    def get_report(self, report_id: str):
        return asyncio.run(self._api.get_report(report_id))


class _SyncMonitoringWrapper:
    def __init__(self, async_api: MonitoringApi) -> None:
        self._api = async_api

    def get_cluster_status(self):
        return asyncio.run(self._api.get_cluster_status())
