"""Interfaces that isolate the core from future Redfish, IPMI, SSH, or serial code."""

from typing import Protocol, runtime_checkable


class DeviceAdapterError(RuntimeError):
    """A controlled device measurement failure."""


class DeviceTimeoutError(DeviceAdapterError):
    """A device measurement exceeded its allowed response window."""


@runtime_checkable
class DeviceAdapter(Protocol):
    source_name: str

    def get_bmc_status(self) -> bool: ...

    def get_firmware_version(self) -> str: ...

    def get_gpu_count(self) -> int: ...

    def get_cpu_temperature(self) -> float: ...
