import numpy as np
import pytest

from xrdbatch.pattern import Pattern


def gaussian(x, center, height, sigma):
    return height * np.exp(-0.5 * ((x - center) / sigma) ** 2)


@pytest.fixture
def synthetic():
    """2θ 10–80°, step 0.02: Gaussian at 30° (h=1000, σ=0.1) on background 50 + 2·2θ, noise σ=5."""
    rng = np.random.default_rng(0)
    tt = np.round(np.arange(10, 80.0001, 0.02), 4)
    y = gaussian(tt, 30.0, 1000, 0.1) + 50 + 2 * tt + rng.normal(0, 5, tt.size)
    return Pattern("synthetic", tt, y)
