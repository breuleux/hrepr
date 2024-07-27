from dataclasses import dataclass
from itertools import count

import pytest
from hrepr import Tag, h, hrepr, returns
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


button_creator = """
function make_button(border) {
    const btn = document.createElement("button");
    btn.innerText = "X";
    btn.style.border = border;
    btn.style.width = "100px";
    return btn;
}
"""


@pytest.fixture(autouse=True)
def reset_id_counter():
    h.current_id = count()
    to_delete = {k for k, v in H.__dict__.items() if isinstance(v, Tag)}
    for k in to_delete:
        delattr(H, k)


def test_global_symbol(file_regression):
    node = H.div(
        H.h2("The button should show 3, 6, 9... when clicked."),
        J(code=incrementer_code).Counter(
            returns(H.button("ERROR!", style="width:100px;")), {"increment": 3}
        ),
    )

    file_regression.check(str(node.as_page()), extension=".html")


def test_stylesheet(file_regression):
    node = H.div(
        H.h2(
            "The page should look purple. Also, the button should show 3, 6, 9... when clicked."
        ),
        J(code=incrementer_code, stylesheet="./stylish.css").Counter(
            returns(H.button("ERROR!", style="width:100px;")), {"increment": 3}
        ),
    )

    file_regression.check(str(node.as_page()), extension=".html")


def test_kwargs(file_regression):
    node = H.div(
        H.h2("The button should show 5, 10, 15... when clicked."),
        J(code=incrementer_code).Counter(
            returns(H.button("ERROR!", style="width:100px;")),
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
        J(namespace="./counter.esm.js").bytwo(
            returns(H.button("ERROR!", style="width:100px;")),
        ),
        J(namespace="./counter.esm.js").by.three(
            returns(H.button("ERROR!", style="width:100px;")),
        ),
        J(module="./counter.esm.js")(
            returns(H.button("ERROR!", style="width:100px;")),
            increment=4,
        ),
    )

    file_regression.check(str(node.as_page()), extension=".html")


def test_script(file_regression):
    node = H.div(
        H.h2("The buttons should increment by 2 and 3 respectively."),
        J(src="./counter.js").bytwo(
            returns(H.button("ERROR!", style="width:100px;")),
        ),
        J(src="./counter.js").by.three(
            returns(H.button("ERROR!", style="width:100px;")),
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


def test_no_varname():
    node = H.div(J()("hello"))
    with pytest.raises(Exception):
        str(node.as_page())


def test_node_creation(file_regression):
    node = H.div(
        H.h2(
            "The button should have a purple border and show 3, 6, 9... when clicked."
        ),
        J(code=incrementer_code).Counter(
            returns(J(code=button_creator).make_button("3px solid purple")),
            {"increment": 3},
        ),
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
    cytoscape = J(
        module="https://cdnjs.cloudflare.com/ajax/libs/cytoscape/3.23.0/cytoscape.esm.min.js",
    )
    node = H.div(
        H.h2("This should show an interactive graph."),
        cytoscape(
            container=returns(
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
        katex.render("c = \\pm\\sqrt{a^2 + b^2}", returns(H.div())),
    )
    file_regression.check(str(node.as_page()), extension=".html")


def test_ids():
    inc = J(code=incrementer_code)

    c1 = inc(returns(H.div()))
    assert c1._get_id() == c1._get_id() == "H2"

    c2 = inc(H.div())
    assert c2._get_id() == "H5" == f"H{c2._serial}"

    c3 = inc(returns(H.div(id="hello")))
    assert c3._get_id() == "hello"

    c4 = inc(returns(inc(returns(H.div(id="wow")))))
    assert c4._get_id() == "wow"

    c5 = inc(inc(returns(H.div(id="yahtzee"))))
    assert c5._get_id() == "yahtzee"


@dataclass
class Toot:
    increment: int

    def __hrepr__(self, H, hrepr):
        return J(code=incrementer_code).Counter(
            returns(H.button("ERROR!", style="width:100px;")),
            increment=self.increment,
        )


def test_j_from_hrepr(file_regression):
    node = H.div(
        H.h2("The button should show 100, 200, 300... when clicked."),
        hrepr(Toot(100)),
    )
    # Little hack to make the output consistent depending on whether the whole suite
    # is run, or only this test.
    file_regression.check(
        str(node.as_page()).replace("H6", "H5"), extension=".html"
    )


def test_as_node(file_regression):
    node = H.div(
        H.h2(
            "The button should show 33, 66, 99... when clicked and should have a magenta border."
        ),
        J(code=incrementer_code)
        .Counter(returns(H.button("ERROR!")), {"increment": 33})
        .as_node(style="width:100px;border:3px solid magenta;"),
    )

    file_regression.check(str(node.as_page()), extension=".html")


def test_exec(file_regression):
    node = H.div(
        H.h2("The box should be blue."),
        H.div("hello", id="thisbox", style="color:white;background:red"),
        J(selector="#thisbox").exec("this.style.background = 'blue';"),
    )

    file_regression.check(str(node.as_page()), extension=".html")


def test_eval(file_regression):
    node = H.div(
        H.h2("The color of the box should be written under it."),
        H.script(
            "function $$REPRESENT(x) { let node = document.createElement('div'); node.innerText = x; return node; }"
        ),
        H.div("hello", id="thisbox", style="color:white;background:red"),
        J(selector="#thisbox").eval("this.style.background"),
    )

    file_regression.check(str(node.as_page()), extension=".html")


def test_suppress_using_exec(file_regression):
    node = H.div(
        H.h2("The button should show 'GOOD!'."),
        J(code=incrementer_creator).make_counter(7).exec(),
    )

    file_regression.check(str(node.as_page()), extension=".html")


def test_object_reference(file_regression):
    node = H.div(
        H.h2("The button should show 103, 106, 109... when clicked."),
        J(code=incrementer_code).Counter(
            returns(H.button("ERROR!", style="width:100px;", id="inc")),
            {"increment": 3},
        ),
        J(object="#inc").exec("this.current += 100"),
    )

    file_regression.check(str(node.as_page()), extension=".html")


def test_thunk(file_regression):
    node = H.div(
        H.h2("The value should increase every 100 milliseconds."),
        H.p(0, id="target"),
        J().setInterval(
            J(selector="#target")
            .exec("this.innerText = Number(this.innerText) + 1")
            .thunk(),
            100,
        ),
    )

    file_regression.check(str(node.as_page()), extension=".html")


def test_j_as_page(file_regression):
    node = J(code=incrementer_code).Counter(
        returns(J(code=button_creator).make_button("3px solid purple")),
        {"increment": 1},
    )

    file_regression.check(str(node.as_page()), extension=".html")
