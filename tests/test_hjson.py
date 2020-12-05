import json

import pytest

from hrepr import hjson

from .common import one_test_per_assert


def same(x):
    return json.dumps(x) == hjson.dumps(x)


@one_test_per_assert
def test_hjson():
    assert same("hello")
    assert same(10)
    assert same(3.14)
    assert same(True)
    assert same(False)
    assert same(None)
    assert same([1, 2, 3])
    assert same(("patate", "au", "four"))
    assert same({"a": 1, "b": (2, 3)})


def test_bad():
    with pytest.raises(TypeError):
        hjson.dumps(object())


class Catapult:
    def power(self):
        return 1e99


@one_test_per_assert
def test_functions():
    assert hjson.dumps(lambda x: x) == "null"
    assert hjson.dumps(Catapult().power) == "null"
