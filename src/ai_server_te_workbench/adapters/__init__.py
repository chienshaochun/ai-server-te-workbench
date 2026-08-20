"""Hardware access boundaries and deterministic simulator adapters."""

from ai_server_te_workbench.adapters.base import (
    DeviceAdapter,
    DeviceAdapterError,
    DeviceTimeoutError,
)
from ai_server_te_workbench.adapters.mock import MockDeviceAdapter, MockFault, MockFaultKind

__all__ = [
    "DeviceAdapter",
    "DeviceAdapterError",
    "DeviceTimeoutError",
    "MockDeviceAdapter",
    "MockFault",
    "MockFaultKind",
]
