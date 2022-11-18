import json

import pytest

from hrepr import embed
from hrepr.h import H
from hrepr.resource import JSExpression, JSFunction, Resource

from .common import one_test_per_assert


def js_embed(obj, **fmt):
    x = embed.js_embed(obj)
    if not isinstance(x, str):
        x = x.to_string(**fmt)
    return x


def attr_embed(obj):
    return embed.attr_embed("k", obj)


def same(x):
    return json.dumps(x) == js_embed(x)


jscode = JSExpression("x = 3")
jsfn = JSFunction("foo", "foo + 1")


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
    assert js_embed(H.div(id="what")) == "document.getElementById('what')"
    assert js_embed([jscode]) == f"[{jscode.code}]"
    assert js_embed(jsfn) == "((foo) => foo + 1)"
    assert js_embed(Resource(list(range(10)))) == js_embed(list(range(10)))


def test_js_embed_bad():
    with pytest.raises(TypeError):
        js_embed(object())

    with pytest.raises(ValueError):
        js_embed(H.div())


@one_test_per_assert
def test_attr_embed():
    assert attr_embed("hello") == "hello"
    assert attr_embed(1234) == "1234"
    assert attr_embed(H.div(id="what")) == "#what"
    assert attr_embed(jscode) is jscode


def test_attr_embed_bad():
    with pytest.raises(TypeError):
        attr_embed(object())

    with pytest.raises(ValueError):
        attr_embed(H.div())
