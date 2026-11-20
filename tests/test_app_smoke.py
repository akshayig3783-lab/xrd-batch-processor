from pathlib import Path

from streamlit.testing.v1 import AppTest

APP = str(Path(__file__).parent.parent / "app.py")
DEMO_FILES = [f for f in (Path(__file__).parent.parent / "sample_data").iterdir() if f.suffix in {".txt", ".brml"}]


def test_demo_data_runs_without_exceptions():
    at = AppTest.from_file(APP, default_timeout=60).run()
    assert not at.exception
    at.button(key="demo").click().run()
    assert not at.exception
    assert len(at.dataframe) >= len(DEMO_FILES) >= 1


def test_app_starts_with_instructions():
    at = AppTest.from_file(APP, default_timeout=60).run()
    assert not at.exception
    assert any("Upload" in i.value or "demo" in i.value for i in at.info)
