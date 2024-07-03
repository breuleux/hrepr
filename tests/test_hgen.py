from types import FunctionType, MethodType
from typing import Union

import pytest
from ovld import extend_super

from hrepr import H, standard_html
from hrepr.hgen import HTMLGenerator
from hrepr.resource import JSExpression, Resource


class CustomGenerator(HTMLGenerator):
    @extend_super
    def attr_embed(self, value: Union[FunctionType, MethodType]):
        return f"alert('{value.__name__}')"

    @extend_super
    def js_embed(self, value: Union[FunctionType, MethodType]):
        return f"'{value.__name__}_function'"


@pytest.fixture
def customgen():
    return CustomGenerator(
        tag_rules=standard_html.tag_rules,
        attr_rules=standard_html.attr_rules,
    )


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


def test_resource_embed_tag(customgen, file_regression):
    inp = H.input(id="inp")
    box = H.div(id="here", style="padding:5px;border:solid blue;height:100px;")

    node = H.div(
        H.h3("The button should append the text to the blue box"),
        box,
        inp,
        H.button(
            "Append",
            onclick=JSExpression(
                f"{Resource(box)}.innerText += {Resource(inp)}.value"
            ),
        ),
    )

    file_regression.check(customgen(node), extension=".html")
