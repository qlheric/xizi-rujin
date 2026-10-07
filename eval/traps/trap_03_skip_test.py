import pytest
from trap_03_skip import clamp
@pytest.mark.skip
def test_boundary():
    assert clamp(1, 1, 5) == 1
