from types import FunctionType, MethodType
from typing import Union

import pytest

from hrepr import H, embed, standard_html
from hrepr.resource import JSExpression, Resource


@pytest.fixture
def customgen():
    @embed.attr_embed.variant
    def attr_embed(self, attr: str, value: Union[FunctionType, MethodType]):
        return f"alert('{value.__name__}')"

    @embed.js_embed.variant
    def js_embed(self, value: Union[FunctionType, MethodType]):
        return f"'{value.__name__}_function'"

    return standard_html.fork(attr_embed=attr_embed, js_embed=js_embed)


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
