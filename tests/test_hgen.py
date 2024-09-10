from html import escape
from types import FunctionType, MethodType
from typing import Union

import pytest
from ovld import extend_super

from hrepr import H, hrepr
from hrepr.hgen import BlockGenerator, HTMLGenerator
from hrepr.resource import JSExpression, Resource


class CustomBlockGenerator(BlockGenerator):
    @extend_super
    def attr_embed(self, value: Union[FunctionType, MethodType]):
        return f"alert('{value.__name__}')"

    @extend_super
    def js_embed(self, value: Union[FunctionType, MethodType]):
        return f"'{value.__name__}_function'"


@pytest.fixture
def customgen():
    return HTMLGenerator(block_generator_class=CustomBlockGenerator)


def test_resource_embed_function(customgen, file_regression):
    def happy(x):
        return x

    node = H.div(
        H.h3("This button alerts the message 'happy'"),
        H.button("happy", onclick=happy),
        H.h3("This button alerts the message 'happy_function'"),
        H.button("happy", onclick=JSExpression(f"alert({Resource(happy)})")),
    )

    file_regression.check(customgen(node), extension=".html")


def test_blockgen(customgen):
    r1 = H.script("alert(1)")
    r2 = H.script("alert(2)")
    r3 = H.script("alert(3)")
    blk1 = customgen.blockgen(H.div("a", resources=r1))
    assert len(blk1.processed_resources) == 1

    blk2 = customgen.blockgen(H.div("b", resources=r2))
    assert len(blk2.processed_resources) == 1

    blk3 = customgen.blockgen(H.div("c", resources=r1))
    assert len(blk3.processed_resources) == 0

    blk4 = customgen.blockgen(H.div("c", resources=[r1, r2, r3]))
    assert len(blk4.processed_resources) == 1


class X:
    def __str__(self):
        return "S"

    def __hrepr__(self, H, hrepr):
        return H.b("H")


def test_embed_object(customgen):
    assert customgen(X()) == "S"
    o = object()
    assert customgen(o) == escape(str(o))


def test_embed_object_hrepr():
    customgen = HTMLGenerator(
        block_generator_class=CustomBlockGenerator, hrepr=hrepr
    )
    assert customgen(X()) == "<b>H</b>"
    o = object()
    assert customgen(o) == str(hrepr(o))
