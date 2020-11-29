from dataclasses import dataclass

from hrepr import H, StdHrepr
from hrepr import hrepr as real_hrepr
from hrepr.h import css_hrepr

from .common import one_test_per_assert

hrepr = StdHrepr.make_interface(fill_resources=False)


@dataclass
class Point:
    x: int
    y: int


class Opaque:
    pass


def hshort(x, **kw):
    return hrepr(x, max_depth=0, **kw)


@one_test_per_assert
def test_singletons():
    assert hrepr(True) == H.span["hreprv-True"]("True")
    assert hrepr(False) == H.span["hreprv-False"]("False")
    assert hrepr(None) == H.span["hreprv-None"]("None")


@one_test_per_assert
def test_numbers():
    assert hrepr(123) == H.span["hreprt-int"]("123")
    assert hrepr(1.25) == H.span["hreprt-float"]("1.25")


@one_test_per_assert
def test_string():
    assert hshort("hello") == H.span["hreprt-str"]("hello")
    assert hrepr("hello this is a bit long") == H.span["hreprt-str"](
        "hello this is a bit long"
    )
    assert hshort("hello this is a bit long") == H.span["hreprt-str"](
        "hello this is a..."
    )
    assert hshort("hello this is a bit long", string_cutoff=10) == H.span[
        "hreprt-str"
    ]("hello...")
    assert hshort("hello this is a bit long", string_cutoff=5) == H.span[
        "hreprt-str"
    ]("...")
    assert hshort("hello this is a bit long", string_cutoff=10000) == H.span[
        "hreprt-str"
    ]("hello this is a bit long")


@one_test_per_assert
def test_bytes():
    assert hrepr(b"hello") == H.span["hreprt-bytes"]("68656c6c6f")
    assert hshort(b"hello") == H.span["hreprt-bytes"]("68656c6c6f")
    assert hrepr(b"hello this is a bit long") == H.span["hreprt-bytes"](
        "68656c6c6f2074686973206973206120626974206c6f6e67"
    )
    assert hshort(b"hello this is a bit long") == H.span["hreprt-bytes"](
        "68656c6c6f2074686..."
    )


def test_structures():
    for typ, o, c in (
        (tuple, "(", ")"),
        (list, "[", "]"),
        (set, "{", "}"),
        (frozenset, "{", "}"),
    ):
        clsname = typ.__name__
        assert hrepr(typ((1, 2))) == H.div[
            f"hreprt-{clsname}", "hrepr-bracketed"
        ](
            H.div["hrepr-open"](o),
            H.div["hrepr-body", "hreprl-h"](
                H.div(H.span["hreprt-int"]("1")),
                H.div(H.span["hreprt-int"]("2")),
            ),
            H.div["hrepr-close"](c),
        )


def test_short_structures():
    for val, o, c in (
        ((1, 2), "(", ")"),
        ([1, 2], "[", "]"),
        ({1, 2}, "{", "}"),
        (frozenset({1, 2}), "{", "}"),
        ({"x": 1, "y": 2}, "{", "}"),
    ):
        clsname = type(val).__name__
        assert hrepr(val, max_depth=0) == H.div[
            f"hreprt-{clsname}", "hrepr-bracketed"
        ](
            H.div["hrepr-open"](o),
            H.div["hrepr-body", "hreprl-s"](H.div("...")),
            H.div["hrepr-close"](c),
        )


def test_dict():
    pt = {"x": 1, "y": 2}
    assert hrepr(pt) == H.div["hreprt-dict", "hrepr-bracketed"](
        H.div["hrepr-open"]("{"),
        H.table["hrepr-body"](
            H.tr(
                H.td(H.span["hreprt-str"]("x")),
                H.td["hrepr-delim"](": "),
                H.td(H.span["hreprt-int"]("1")),
            ),
            H.tr(
                H.td(H.span["hreprt-str"]("y")),
                H.td["hrepr-delim"](": "),
                H.td(H.span["hreprt-int"]("2")),
            ),
        ),
        H.div["hrepr-close"]("}"),
    )


def test_dataclass():
    pt = Point(1, 2)

    assert hrepr(pt) == H.div["hreprt-Point", "hrepr-instance", "hreprl-v"](
        H.div["hrepr-title"]("Point"),
        H.table["hrepr-body"](
            H.tr(
                H.td(H.span["hrepr-symbol"]("x")),
                H.td["hrepr-delim"]("="),
                H.td(H.span["hreprt-int"]("1")),
            ),
            H.tr(
                H.td(H.span["hrepr-symbol"]("y")),
                H.td["hrepr-delim"]("="),
                H.td(H.span["hreprt-int"]("2")),
            ),
        ),
    )

    assert hrepr(pt, max_depth=0) == H.div[
        "hreprt-Point", "hrepr-instance", "hreprl-s"
    ](
        H.div["hrepr-title"]("Point"),
        H.div["hrepr-body", "hreprl-s"](H.div("...")),
    )


def test_tag():
    tg = H.span["hello"](1, 2, H.b("there"))
    assert hrepr(tg) == tg


def test_multiref():
    li = [1, 2]
    lili = [li, li]

    assert hrepr(lili) == H.div["hreprt-list", "hrepr-bracketed"](
        H.div["hrepr-open"]("["),
        H.div["hrepr-body", "hreprl-h"](
            H.div(
                H.div["hrepr-refbox"](
                    H.span["hrepr-ref"]("#", 1, "="),
                    H.div["hreprt-list", "hrepr-bracketed"](
                        H.div["hrepr-open"]("["),
                        H.div["hrepr-body", "hreprl-h"](
                            H.div(H.span["hreprt-int"]("1")),
                            H.div(H.span["hreprt-int"]("2")),
                        ),
                        H.div["hrepr-close"]("]"),
                    ),
                )
            ),
            H.div(
                H.div["hrepr-refbox"](
                    H.span["hrepr-ref"]("#", 1, "="),
                    H.div["hreprt-list", "hrepr-bracketed"](
                        H.div["hrepr-open"]("["),
                        H.div["hrepr-body", "hreprl-s"](H.div("..."),),
                        H.div["hrepr-close"]("]"),
                    ),
                )
            ),
        ),
        H.div["hrepr-close"]("]"),
    )

    assert hrepr(lili, shortrefs=True) == H.div[
        "hreprt-list", "hrepr-bracketed"
    ](
        H.div["hrepr-open"]("["),
        H.div["hrepr-body", "hreprl-h"](
            H.div(
                H.div["hrepr-refbox"](
                    H.span["hrepr-ref"]("#", 1, "="),
                    H.div["hreprt-list", "hrepr-bracketed"](
                        H.div["hrepr-open"]("["),
                        H.div["hrepr-body", "hreprl-h"](
                            H.div(H.span["hreprt-int"]("1")),
                            H.div(H.span["hreprt-int"]("2")),
                        ),
                        H.div["hrepr-close"]("]"),
                    ),
                )
            ),
            H.div(H.span["hrepr-ref"]("#", 1)),
        ),
        H.div["hrepr-close"]("]"),
    )


def test_recursive():
    li = [1]
    li.append(li)

    assert hrepr(li) == H.div["hrepr-refbox"](
        H.span["hrepr-ref"]("#", 1, "="),
        H.div["hreprt-list", "hrepr-bracketed"](
            H.div["hrepr-open"]("["),
            H.div["hreprl-h", "hrepr-body"](
                H.div(H.span["hreprt-int"]("1")),
                H.div(
                    H.div["hrepr-refbox"](
                        H.span["hrepr-ref"]("⟳", 1, "="),
                        H.div["hreprt-list", "hrepr-bracketed"](
                            H.div["hrepr-open"]("["),
                            H.div["hrepr-body", "hreprl-s"](H.div("..."),),
                            H.div["hrepr-close"]("]"),
                        ),
                    )
                ),
            ),
            H.div["hrepr-close"]("]"),
        ),
    )

    assert hrepr(li, shortrefs=True) == H.div["hrepr-refbox"](
        H.span["hrepr-ref"]("#", 1, "="),
        H.div["hreprt-list", "hrepr-bracketed"](
            H.div["hrepr-open"]("["),
            H.div["hreprl-h", "hrepr-body"](
                H.div(H.span["hreprt-int"]("1")),
                H.div(H.span["hrepr-ref"]("⟳", 1)),
            ),
            H.div["hrepr-close"]("]"),
        ),
    )


def test_unsupported():
    assert hshort(Opaque()) == H.span["hreprs-Opaque"]("<", "Opaque", ">")


def test_as_page():
    utf8 = H.meta(
        {"http-equiv": "Content-type"}, content="text/html", charset="UTF-8"
    )
    assert real_hrepr.page(1) == H.inline(
        H.raw("<!DOCTYPE html>"),
        H.html(H.head(utf8, H.style(css_hrepr)), H.body(real_hrepr(1)),),
    )


def test_hrepr_multiarg():
    assert hrepr(1, 2) == H.inline(
        H.span["hreprt-int"]("1"), H.span["hreprt-int"]("2"),
    )


def test_preprocess():
    assert hrepr(1, preprocess=lambda x, hrepr: x + 1) == H.span["hreprt-int"](
        "2"
    )


def test_postprocess():
    assert hrepr(1, postprocess=lambda x, obj, hrepr: x["newclass"]) == H.span[
        "hreprt-int", "newclass"
    ]("1")
