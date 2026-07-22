"""
Platform 7 Façades Package Initialization.
"""

from akaal.api.facades.base import IFacade
from akaal.api.facades.platform1 import IPlatform1Facade, Platform1Facade
from akaal.api.facades.platform2 import IPlatform2Facade, Platform2Facade
from akaal.api.facades.platform3 import Platform3Facade
from akaal.api.facades.platform4 import Platform4Facade
from akaal.api.facades.platform5 import IPlatform5Facade, Platform5Facade
from akaal.api.facades.platform6 import Platform6Facade
from akaal.api.facades.platform8 import Platform8Facade
from akaal.api.facades.platform9 import Platform9Facade

__all__ = [
    "IFacade",
    "IPlatform1Facade",
    "Platform1Facade",
    "IPlatform2Facade",
    "Platform2Facade",
    "Platform3Facade",
    "Platform4Facade",
    "IPlatform5Facade",
    "Platform5Facade",
    "Platform6Facade",
    "Platform8Facade",
    "Platform9Facade",
]
