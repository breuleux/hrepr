from hrepr.textgen import Breakable, Sequence, Text

from tests.common import one_test_per_assert


@one_test_per_assert
def test_empty():
    assert Text("").empty()
    assert not Text(" ").empty()
    assert not Text("x").empty()

    assert Breakable(start="", end="", body=[]).empty()
    assert not Breakable(start="(", end=")", body=[]).empty()

    assert Sequence().empty()
    assert not Sequence("x").empty()
