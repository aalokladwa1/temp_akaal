"""
CDC API package initialization.
"""

from akaal.cdc.api.client import CDCClient
from akaal.cdc.api.facade import IPlatform4Facade, Platform4Facade

__all__ = ["CDCClient", "IPlatform4Facade", "Platform4Facade"]
