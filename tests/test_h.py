from itertools import count

from hrepr import H, Tag
from hrepr import h as hmodule

from .common import one_test_per_assert


def reset_id_counter():
    hmodule.id_counter = count()


def matches(h, s):
    return str(h) == s


@one_test_per_assert
def test_div():
    assert matches(H.div(), "<div></div>")
    assert matches(H.div("Some content"), "<div>Some content</div>")
    assert matches(
        H.div("  \n\n    Some  content \n      "),
        "<div>  \n\n    Some  content \n      </div>",
    )
    assert matches(H.div["classy"](), '<div class="classy"></div>')
    assert matches(H.div["classy"](), '<div class="classy"></div>')
    assert matches(
        H.div["classy"](id="eyedee", thing="thang"),
        '<div class="classy" id="eyedee" thing="thang"></div>',
    )
    assert matches(H.div(dash_es=True), "<div dash-es></div>")
    assert matches(
        H.div.fill(attributes={"un_der_scores": True}),
        "<div un_der_scores></div>",
    )
    assert matches(
        H.div['qu"ote'](id='qu"ite'),
        '<div class="qu&quot;ote" id="qu&quot;ite"></div>',
    )


@one_test_per_assert
def test_nesting():
    assert matches(
        H.div(H.div(H.b("inner"))), "<div><div><b>inner</b></div></div>"
    )
    assert matches(
        H.div(H.b("hello"), H.i("there")), "<div><b>hello</b><i>there</i></div>"
    )
    assert matches(
        H.div([[[H.b("hello"), [H.i("there")]]]]),
        "<div><b>hello</b><i>there</i></div>",
    )


def test_quote():
    assert matches(H.div("<quoted>"), "<div>&lt;quoted&gt;</div>")


@one_test_per_assert
def test_raw():
    assert matches(H.raw("thing"), "thing")
    assert matches(H.raw("<b>hello</b>"), "<b>hello</b>")
    assert matches(
        H.raw(H.b("hello"), H.i("there")), "<b>hello</b><i>there</i>"
    )
    assert matches(H.raw(H.b("<inner>")), "<b>&lt;inner&gt;</b>")


@one_test_per_assert
def test_inline():
    assert matches(H.inline("thing"), "thing")
    assert matches(H.inline("<b>hello</b>"), "&lt;b&gt;hello&lt;/b&gt;")
    assert matches(
        H.inline(H.b("hello"), H.i("there")), "<b>hello</b><i>there</i>"
    )


def test_script():
    assert matches(H.script("1 < 2; 4 > 3;"), "<script>1 < 2; 4 > 3;</script>")


def test_style():
    assert matches(
        H.style("a < b { color: red; }"), "<style>a < b { color: red; }</style>"
    )


@one_test_per_assert
def test_voids():
    assert matches(H.area(), "<area />")
    assert matches(H.base(), "<base />")
    assert matches(H.br(), "<br />")
    assert matches(H.col(), "<col />")
    assert matches(H.command(), "<command />")
    assert matches(H.embed(), "<embed />")
    assert matches(H.hr(), "<hr />")
    assert matches(H.img(), "<img />")
    assert matches(H.input(), "<input />")
    assert matches(H.keygen(), "<keygen />")
    assert matches(H.link(), "<link />")
    assert matches(H.meta(), "<meta />")
    assert matches(H.param(), "<param />")
    assert matches(H.source(), "<source />")
    assert matches(H.track(), "<track />")
    assert matches(H.wbr(), "<wbr />")


def test_incremental():
    d0 = H.div()
    assert matches(d0, "<div></div>")

    d = d0("crumpet")
    assert matches(d0, "<div></div>")
    assert matches(d, "<div>crumpet</div>")

    d = d(H.b("tea"))
    assert matches(d, "<div>crumpet<b>tea</b></div>")

    d = d(id="paramount")
    assert matches(d, '<div id="paramount">crumpet<b>tea</b></div>')

    d = d({"sheep": "bah"}, quack=True)
    assert matches(
        d, '<div id="paramount" sheep="bah" quack>crumpet<b>tea</b></div>'
    )

    d = d(quack=False)
    assert matches(d, '<div id="paramount" sheep="bah">crumpet<b>tea</b></div>')


@one_test_per_assert
def test_misc():
    assert matches(H.whimsy("cal"), "<whimsy>cal</whimsy>")
    assert H.div(H.b("hello")) == H.div(H.b("hello"))
    assert H.div(H.b("hello")) != H.div(H.i("hello"))
    assert isinstance(hash(H.div(H.div("yay!"))), int)
    assert repr(H.div("soupe")) == str(H.div("soupe"))


def test_dash():
    assert matches(H.some_tag("xyz"), "<some-tag>xyz</some-tag>")


def test_as_page():
    tag = H.div("simplicity")
    utf8 = H.meta(
        {"http-equiv": "Content-type"}, content="text/html", charset="UTF-8"
    )
    page = H.inline(
        H.raw("<!DOCTYPE html>"), H.html(H.head(utf8), H.body(tag)),
    )
    assert tag.as_page() == page


def test_as_page_with_resources():
    sty = H.style("b { color: red; }")
    scr = H.script("x = 1234;")
    resources = (sty, scr)
    inner = H.b("resources").fill(resources=scr)
    tag = H.div("with ", inner).fill(resources=sty)
    utf8 = H.meta(
        {"http-equiv": "Content-type"}, content="text/html", charset="UTF-8"
    )
    page = H.inline(
        H.raw("<!DOCTYPE html>"), H.html(H.head(utf8, *resources), H.body(tag)),
    )
    assert tag.as_page() == page


def test_subclasses():
    tspan = type(H.span())
    tdiv1 = type(H.div["straw"])
    tdiv2 = type(H.div["straw"]("berry"))

    assert tspan is not Tag
    assert tdiv1 is not Tag
    assert tdiv1 is tdiv2
    assert issubclass(tspan, Tag)
    assert issubclass(tdiv1, Tag)


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
    reset_id_counter()

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
    reset_id_counter()

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
    reset_id_counter()

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
