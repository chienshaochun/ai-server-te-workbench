"""Deterministic simulated hardware measurements with explicit fault injection."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from enum import Enum

from ai_server_te_workbench.adapters.base import DeviceAdapterError, DeviceTimeoutError
from ai_server_te_workbench.models import DeviceUnderTest, JsonScalar


class MockFaultKind(str, Enum):
    TIMEOUT = "timeout"
    READ_ERROR = "read_error"


@dataclass(frozen=True)
class MockFault:
    test_case_id: str
    kind: MockFaultKind
    repeat: int = 1

    def __post_init__(self) -> None:
        if not isinstance(self.test_case_id, str) or not self.test_case_id:
            raise ValueError("test_case_id is required")
        if not isinstance(self.kind, MockFaultKind):
            raise TypeError("kind must be a MockFaultKind")
        if not isinstance(self.repeat, int) or isinstance(self.repeat, bool):
            raise TypeError("repeat must be an integer")
        if not 1 <= self.repeat <= 6:
            raise ValueError("repeat must be between 1 and 6")


class MockDeviceAdapter:
    source_name = "mock_device_adapter"

    def __init__(self, dut: DeviceUnderTest, faults: tuple[MockFault, ...] = ()) -> None:
        if not isinstance(dut, DeviceUnderTest):
            raise TypeError("dut must be a DeviceUnderTest")
        if isinstance(faults, list):
            faults = tuple(faults)
        if not isinstance(faults, tuple) or not all(
            isinstance(fault, MockFault) for fault in faults
        ):
            raise TypeError("faults must contain only MockFault values")
        if len({fault.test_case_id for fault in faults}) != len(faults):
            raise ValueError("only one mock fault is allowed per test case")
        self._dut = dut
        self._faults = {fault.test_case_id: fault for fault in faults}
        self._calls: Counter[str] = Counter()

    def get_bmc_status(self) -> bool:
        return bool(self._read("bmc_connectivity", self._dut.bmc_reachable))

    def get_firmware_version(self) -> str:
        return str(self._read("firmware_version", self._dut.firmware_version))

    def get_gpu_count(self) -> int:
        return int(self._read("gpu_device_count", self._dut.gpu_count))

    def get_cpu_temperature(self) -> float:
        return float(self._read("cpu_temperature", self._dut.cpu_temperature_c))

    def call_count(self, test_case_id: str | None = None) -> int:
        if test_case_id is None:
            return sum(self._calls.values())
        return self._calls[test_case_id]

    def _read(self, test_case_id: str, value: JsonScalar) -> JsonScalar:
        self._calls[test_case_id] += 1
        fault = self._faults.get(test_case_id)
        if fault is not None and self._calls[test_case_id] <= fault.repeat:
            if fault.kind == MockFaultKind.TIMEOUT:
                raise DeviceTimeoutError(f"simulated timeout while reading {test_case_id}")
            raise DeviceAdapterError(f"simulated read error while reading {test_case_id}")
        return value
