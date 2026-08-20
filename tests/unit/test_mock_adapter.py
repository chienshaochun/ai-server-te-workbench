import pytest

from ai_server_te_workbench.adapters import (
    DeviceAdapterError,
    DeviceTimeoutError,
    MockDeviceAdapter,
    MockFault,
    MockFaultKind,
)
from ai_server_te_workbench.scenarios import built_in_scenarios


def healthy_dut():
    return built_in_scenarios()[0].dut


def test_mock_adapter_reads_all_four_dut_measurements() -> None:
    adapter = MockDeviceAdapter(healthy_dut())

    assert adapter.get_bmc_status() is True
    assert adapter.get_firmware_version() == "1.2.0"
    assert adapter.get_gpu_count() == 4
    assert adapter.get_cpu_temperature() == 62.0
    assert adapter.call_count() == 4


def test_timeout_fault_repeats_then_returns_real_measurement() -> None:
    adapter = MockDeviceAdapter(
        healthy_dut(),
        faults=(MockFault("bmc_connectivity", MockFaultKind.TIMEOUT, repeat=2),),
    )

    with pytest.raises(DeviceTimeoutError, match="simulated timeout"):
        adapter.get_bmc_status()
    with pytest.raises(DeviceTimeoutError):
        adapter.get_bmc_status()

    assert adapter.get_bmc_status() is True
    assert adapter.call_count("bmc_connectivity") == 3


def test_read_error_fault_is_distinct_from_timeout() -> None:
    adapter = MockDeviceAdapter(
        healthy_dut(),
        faults=(MockFault("gpu_device_count", MockFaultKind.READ_ERROR),),
    )

    with pytest.raises(DeviceAdapterError, match="simulated read error"):
        adapter.get_gpu_count()


def test_adapter_rejects_duplicate_fault_definitions() -> None:
    with pytest.raises(ValueError, match="one mock fault"):
        MockDeviceAdapter(
            healthy_dut(),
            faults=(
                MockFault("bmc_connectivity", MockFaultKind.TIMEOUT),
                MockFault("bmc_connectivity", MockFaultKind.READ_ERROR),
            ),
        )


@pytest.mark.parametrize("repeat", [0, 7])
def test_fault_repeat_is_limited_to_runner_retry_boundary(repeat: int) -> None:
    with pytest.raises(ValueError):
        MockFault("bmc_connectivity", MockFaultKind.TIMEOUT, repeat=repeat)
