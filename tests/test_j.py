from itertools import count

import pytest

from hrepr import h as hmodule
from hrepr import into
from hrepr.h import H
from hrepr.j import J

incrementer_code = """
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


@pytest.fixture(autouse=True)
def reset_id_counter():
    hmodule.current_autoid = count()


def test_global_symbol(file_regression):
    node = H.div(
        H.h2("The button should show 3, 6, 9... when clicked."),
        J(code=incrementer_code).Counter(
            into(H.button("ERROR!", style="width:100px;")), {"increment": 3}
        ),
    )

    file_regression.check(str(node.as_page()), extension=".html")


def test_stylesheet(file_regression):
    node = H.div(
        H.h2(
            "The page should look purple. Also, the button should show 3, 6, 9... when clicked."
        ),
        J(code=incrementer_code, stylesheet="./stylish.css").Counter(
            into(H.button("ERROR!", style="width:100px;")), {"increment": 3}
        ),
    )

    file_regression.check(str(node.as_page()), extension=".html")


def test_kwargs(file_regression):
    node = H.div(
        H.h2("The button should show 5, 10, 15... when clicked."),
        J(code=incrementer_code).Counter(
            into(H.button("ERROR!", style="width:100px;")),
            increment=5,
        ),
    )

    file_regression.check(str(node.as_page()), extension=".html")


def test_module(file_regression):
    node = H.div(
        H.h2("The buttons should increment by 2, 3 and 4 respectively."),
        H.h4(
            "Note: this will NOT work when browsing the file directly, ",
            "view using a server e.g. with `python -m http.server`.",
        ),
        J(module="./counter.esm.js", symbol="bytwo")(
            into(H.button("ERROR!", style="width:100px;")),
        ),
        J(namespace="./counter.esm.js").by.three(
            into(H.button("ERROR!", style="width:100px;")),
        ),
        J(module="./counter.esm.js")(
            into(H.button("ERROR!", style="width:100px;")),
            increment=4,
        ),
    )

    file_regression.check(str(node.as_page()), extension=".html")


def test_script(file_regression):
    node = H.div(
        H.h2("The buttons should increment by 2 and 3 respectively."),
        J(src="./counter.js", symbol="bytwo")(
            into(H.button("ERROR!", style="width:100px;")),
        ),
        J(src="./counter.js").by.three(
            into(H.button("ERROR!", style="width:100px;")),
        ),
    )

    file_regression.check(str(node.as_page()), extension=".html")


incrementer_creator = """
function make_counter(increment) {
    let node = document.createElement("button");
    let current = 0;
    node.innerText = "Click me!";
    node.style.width = "100px";
    node.onclick = evt => {
        current += increment;
        node.innerText = current;
    };
    return node;
}
"""


def test_js_returns_node(file_regression):
    node = H.div(
        H.h2("The button should increment by 7."),
        J(code=incrementer_creator).make_counter(7),
    )

    file_regression.check(str(node.as_page()), extension=".html")


def test_alert(file_regression):
    node = H.div(
        H.h2("There should be an alert."),
        J().alert("hello"),
    )

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


def test_external_cytoscape(file_regression):
    node = H.div(
        H.h2("This should show an interactive graph."),
        J(
            module="https://cdnjs.cloudflare.com/ajax/libs/cytoscape/3.23.0/cytoscape.esm.min.js"
        )(
            container=into(
                H.div(
                    style={
                        "width": "500px",
                        "height": "500px",
                        "border": "1px solid cyan",
                    },
                )
            ),
            elements=[
                {"data": {"id": "A"}},
                {"data": {"id": "B"}},
                {"data": {"id": "C"}},
                {"data": {"source": "A", "target": "B"}},
                {"data": {"source": "B", "target": "C"}},
                {"data": {"source": "C", "target": "A"}},
            ],
            style=cystyle,
            layout={"name": "cose"},
        ),
    )
    file_regression.check(str(node.as_page()), extension=".html")


def test_external_katex(file_regression):
    katex = J(
        module="https://cdn.jsdelivr.net/npm/katex@0.16.4/dist/katex.mjs",
        stylesheet="https://cdn.jsdelivr.net/npm/katex@0.16.4/dist/katex.css",
    )
    node = H.div(
        H.h2("This should show a well-formatted mathematical formula."),
        katex.render("c = \\pm\\sqrt{a^2 + b^2}", into(H.div())),
    )
    file_regression.check(str(node.as_page()), extension=".html")
