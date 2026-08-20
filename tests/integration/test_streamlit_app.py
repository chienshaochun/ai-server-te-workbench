from pathlib import Path

from streamlit.testing.v1 import AppTest


APP_PATH = Path(__file__).parents[2] / "app.py"


def load_app() -> AppTest:
    app = AppTest.from_file(APP_PATH).run(timeout=20)
    assert len(app.exception) == 0
    return app


def button(app: AppTest, label: str):
    return next(item for item in app.button if item.label == label)


def test_app_loads_with_common_issue_entry_and_safety_boundary() -> None:
    app = load_app()

    assert app.title[0].value == "AI Server TE Guided Troubleshooting"
    assert app.text_input[0].label == "Server 型號"
    assert "synthetic demo history" in app.selectbox[0].label
    assert any("不控制" in item.value for item in app.warning)


def test_common_network_issue_completes_three_step_report_flow() -> None:
    app = load_app()
    app.text_input[0].input("AI Server X1")
    button(app, "開始逐步排查").click()
    app.run(timeout=20)

    for _ in range(3):
        button(app, "提交這一步").click()
        app.run(timeout=20)
        assert len(app.exception) == 0

    assert any("resolved" in item.value for item in app.success)
    assert any("預覽報告" == item.label for item in app.expander)
    assert app.metric[2].value == "resolved"


def test_free_text_comparative_issue_starts_one_unit_flow() -> None:
    app = load_app()
    app.text_input[0].input("Model Z")
    app.radio[0].set_value("自由文字")
    app.run(timeout=20)
    app.text_area[0].input("這台可以但另一台不行")
    button(app, "開始逐步排查").click()
    app.run(timeout=20)

    assert len(app.exception) == 0
    assert app.metric[1].value == "one_unit_only"
    assert any("相同 station" in item.label for item in app.radio)


def test_symbol_only_model_shows_validation_message_without_crashing() -> None:
    app = load_app()
    app.text_input[0].input("---")
    app.run(timeout=20)
    button(app, "開始逐步排查").click()
    app.run(timeout=20)

    assert len(app.exception) == 0
    assert any("Server 型號" in item.value for item in app.error)
