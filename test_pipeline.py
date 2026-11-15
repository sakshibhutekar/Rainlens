import numpy as np
from pipeline import accum_to_rain, precipitation_metres

def test_accumulation_differences():
    got = accum_to_rain(np.array([0.001, 0.0035, 0.004]))
    np.testing.assert_allclose(got, [1, 2.5, 0.5])

def test_reset_fails():
    try:
        accum_to_rain(np.array([0.004, 0.001]))
    except AssertionError:
        return
    raise AssertionError("large accumulation reset was accepted")

def test_aifs_units_normalize_to_metres():
    np.testing.assert_allclose(precipitation_metres(np.array([1.0, 37.5]), "kg m**-2"), [0.001, 0.0375])
    np.testing.assert_allclose(precipitation_metres(np.array([0.001, 0.0375]), "m"), [0.001, 0.0375])

if __name__ == "__main__":
    test_accumulation_differences()
    test_reset_fails()
    test_aifs_units_normalize_to_metres()
    print("pipeline checks passed")
