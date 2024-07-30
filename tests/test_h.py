from itertools import count

import pytest
from hrepr import H, Tag, h

from .common import one_test_per_assert


@pytest.fixture(autouse=True)
def reset_id_counter():
    h.current_id = count()
    to_delete = {k for k, v in H.__dict__.items() if isinstance(v, Tag)}
    for k in to_delete:
        delattr(H, k)


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
        '<div class="classy" thing="thang" id="eyedee"></div>',
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


class Hobbit:
    def __h__(self):
        return H.b("preciouss")


def test_dunder_h():
    assert matches(H.div(Hobbit()), "<div><b>preciouss</b></div>")


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


def test_ensure_id():
    # First time
    assert matches(H.div("wow").ensure_id(), '<div id="H1">wow</div>')
    # Second time
    assert matches(H.div("wow").ensure_id(), '<div id="H2">wow</div>')
    # Shorthand
    assert matches(H.div("wow", id=True), '<div id="H3">wow</div>')
    # Already has an id
    assert matches(
        H.div("wow", id="xxx").ensure_id(), '<div id="xxx">wow</div>'
    )


def test_cannot_ensure_id():
    d = H.div("hello")
    str(d)
    with pytest.raises(
        Exception, match="It is too late to ensure that this node has an ID"
    ):
        d.ensure_id()


def test_as_page():
    tag = H.div("simplicity")
    utf8 = H.meta(
        {"http-equiv": "Content-type"}, content="text/html", charset="UTF-8"
    )
    page = H.inline(
        H.raw("<!DOCTYPE html>"),
        H.html(H.head(utf8), H.body(tag)),
    )
    assert tag.as_page() == str(page)


def test_as_page_with_resources():
    sty = H.style("b { color: red; }")
    scr = H.script("x = 1234;")
    resources = (sty, scr)
    inner = H.b("resources").fill(resources=scr)
    tag = H.div("with ", inner, resources=sty)  # Other way to specify resources
    utf8 = H.meta(
        {"http-equiv": "Content-type"}, content="text/html", charset="UTF-8"
    )
    page = H.inline(
        H.raw("<!DOCTYPE html>"),
        H.html(H.head(utf8, *resources), H.body(tag)),
    )
    assert tag.as_page() == str(page)


def test_subclasses():
    tspan = type(H.span())
    tdiv1 = type(H.div["straw"])
    tdiv2 = type(H.div["straw"]("berry"))

    assert tspan is not Tag
    assert tdiv1 is not Tag
    assert tdiv1 is tdiv2
    assert issubclass(tspan, Tag)
    assert issubclass(tdiv1, Tag)


def test_import_elements():
    from hrepr.elements import div, span

    assert div("hello", span("world")) == H.div("hello", H.span("world"))
