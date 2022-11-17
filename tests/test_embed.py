import json

import pytest

from hrepr import embed

from .common import one_test_per_assert


def js_embed_s(obj, **fmt):
    return embed.js_embed(obj).to_string(**fmt)


def same(x):
    return json.dumps(x) == js_embed_s(x)


@one_test_per_assert
def test_js_embed():
    assert same("hello")
    assert same(10)
    assert same(3.14)
    assert same(True)
    assert same(False)
    assert same(None)
    assert same([1, 2, 3])
    assert same(("patate", "au", "four"))
    assert same({"a": 1, "b": (2, 3)})
    assert same({})
    assert same([])
    assert same([[[[]]]])


def test_bad():
    with pytest.raises(TypeError):
        js_embed_s(object())


# class Catapult:
#     def power(self):
#         return 1e99


# @one_test_per_assert
# def test_functions():
#     assert js_embed_s(lambda x: x) == "null"
#     assert js_embed_s(Catapult().power) == "null"
