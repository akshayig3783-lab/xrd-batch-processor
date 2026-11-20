import pytest

from xrdbatch.reference import allowed_two_theta, read_rruff_cell


def test_read_rruff_cell(tmp_path):
    f = tmp_path / "q.txt"
    f.write_text("##CELL PARAMETERS=a: 4.9134 b: 4.9134 c: 5.4042 alpha: 90 beta: 90 gamma: 120 volume: 112.991 crystal system: hexagonal\n5, 0\n")
    cell = read_rruff_cell(f)
    assert cell["a"] == pytest.approx(4.9134) and cell["c"] == pytest.approx(5.4042)
    assert cell["gamma"] == 120 and cell["system"] == "hexagonal"


def test_quartz_reflections_include_known_lines():
    cell = {"a": 4.9134, "b": 4.9134, "c": 5.4042, "alpha": 90, "beta": 90, "gamma": 120, "system": "hexagonal"}
    tt = allowed_two_theta(cell, wavelength=1.5406, tt_max=60, rule="P3221")
    # quartz (100) 20.86°, (101) 26.64°, (110) 36.54°, (112) 50.14° for Cu Kα1
    for ref in [20.86, 26.64, 36.54, 50.14]:
        assert min(abs(t - ref) for t in tt) < 0.03
    # (001) at 16.4° is forbidden by the 3_2 screw axis
    assert min(abs(t - 16.39) for t in tt) > 0.5


def test_r3c_centering_removes_forbidden():
    cell = {"a": 4.759, "b": 4.759, "c": 12.991, "alpha": 90, "beta": 90, "gamma": 120, "system": "hexagonal"}
    tt = allowed_two_theta(cell, wavelength=1.5406, tt_max=40, rule="R-3c")
    # corundum (012) 25.58°, (104) 35.15° allowed; (100) at 21.6° forbidden
    assert min(abs(t - 25.58) for t in tt) < 0.05
    assert min(abs(t - 35.15) for t in tt) < 0.05
    assert min(abs(t - 21.56) for t in tt) > 0.3
