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


def test_prepare_exports_and_duplicate_demo_load():
    at = AppTest.from_file(APP, default_timeout=60).run()
    at.button(key="demo").click().run()
    at.button(key="prepare_exports").click().run()
    assert not at.exception


def test_crop_outside_all_data_does_not_crash():
    at = AppTest.from_file(APP, default_timeout=60).run()
    at.button(key="demo").click().run()
    at.slider[0].set_value((150.0, 160.0)).run()
    assert not at.exception
    assert any("no data left" in w.value for w in at.warning)
