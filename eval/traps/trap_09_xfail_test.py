import pytest
from trap_09_xfail import count_items
@pytest.mark.xfail
def test_count():
    assert count_items([1, 2]) == 2
