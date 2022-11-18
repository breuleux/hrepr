from types import FunctionType, MethodType
from typing import Union

import pytest

from hrepr import H, embed, standard_html
from hrepr.hgen import HTMLGenerator
from hrepr.resource import JSExpression, Resource

incrementer_script = H.script(
    """
    class Counter {
        constructor(node, options) {
            this.node = node;
            this.increment = options.increment;
            this.current = 0;
            this.node.innerText = "Click me!";
            this.node.onclick = evt => {
                this.current += this.increment;
                this.node.innerText = this.current;
            }
        }
    }
    """
)


def test_constructor_global_symbol(file_regression):
    node = H.div(
        H.h2("The button should show 3, 6, 9... when clicked."),
        H.button(
            "ERROR!",  # Will only show if the button's text is not set by the script
            style="width:100px;",
            constructor={"symbol": "Counter", "options": {"increment": 3,}},
        ),
    ).fill(resources=incrementer_script)

    file_regression.check(str(node.as_page()), extension=".html")


def test_constructor_multiple(file_regression):
    node = H.div(
        H.h2("The buttons should increment by 2 and 3 respectively."),
        H.button(
            "ERROR!",
            style="width:100px;",
            constructor={"symbol": "Counter", "options": {"increment": 2,}},
        ),
        H.button(
            "ERROR!",
            style="width:100px;",
            constructor={"symbol": "Counter", "options": {"increment": 3,}},
        ),
    ).fill(resources=incrementer_script)

    file_regression.check(str(node.as_page()), extension=".html")


cystyle = """
node {
    background-color: #080;
    label: data(id);
}
edge {
    width: 5;
    line-color: #ccc;
    target-arrow-color: #ccc;
    target-arrow-shape: triangle;
    curve-style: bezier;
}
"""


def test_constructor_cytoscape(file_regression):
    node = H.div(
        H.h2("This should show an interactive graph."),
        H.div(
            style="width:500px;height:500px;border:1px solid black;",
            constructor={
                "module": "https://cdnjs.cloudflare.com/ajax/libs/cytoscape/3.23.0/cytoscape.esm.min.js",
                "arguments": {
                    "container": H.self(),
                    "elements": [
                        {"data": {"id": "A"}},
                        {"data": {"id": "B"}},
                        {"data": {"id": "C"}},
                        {"data": {"source": "A", "target": "B"}},
                        {"data": {"source": "B", "target": "C"}},
                        {"data": {"source": "C", "target": "A"}},
                    ],
                    "style": cystyle,
                    "layout": {"name": "cose"},
                },
            },
        ),
    )

    file_regression.check(str(node.as_page()), extension=".html")


@pytest.fixture
def customgen():
    @embed.attr_embed.variant
    def attr_embed(self, attr: str, value: Union[FunctionType, MethodType]):
        return f"alert('{value.__name__}')"

    @embed.js_embed.variant
    def js_embed(self, value: Union[FunctionType, MethodType]):
        return f"'{value.__name__}_function'"

    return HTMLGenerator(
        rules=standard_html.rules, attr_embed=attr_embed, js_embed=js_embed
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
    box = H.div(id="here", style="padding:5px;border:solid blue")

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


# def test_resource_module_extraction
