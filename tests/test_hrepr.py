from dataclasses import dataclass

from hrepr import H, StdHrepr

from .common import one_test_per_assert

hrepr = StdHrepr.make_interface(fill_resources=False).hrepr


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
            f"hreprt-{clsname}", "hrepr-titled-h"
        ](
            H.div["hrepr-title"](o),
            H.div["hrepr-contents-h"](
                H.span["hreprt-int"]("1"), H.span["hreprt-int"]("2"),
            ),
            H.div["hrepr-title"](c),
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
        assert hrepr(val, max_depth=0) == H.span[f"hreprs-{clsname}"](
            f"{o}...{c}"
        )


def test_dict():
    pt = {"x": 1, "y": 2}
    assert hrepr(pt) == H.div[f"hreprt-dict", "hrepr-titled-h"](
        H.div["hrepr-title"]("{"),
        H.div["hrepr-contents-v"](
            H.table["hrepr-instance-table"](
                H.tr(
                    H.td(H.span["hreprt-str"]("x")),
                    H.td["hrepr-delimiter"](" ↦ "),
                    H.td(H.span["hreprt-int"]("1")),
                ),
                H.tr(
                    H.td(H.span["hreprt-str"]("y")),
                    H.td["hrepr-delimiter"](" ↦ "),
                    H.td(H.span["hreprt-int"]("2")),
                ),
            )
        ),
        H.div["hrepr-title"]("}"),
    )


def test_dataclass():
    pt = Point(1, 2)
    assert hrepr(pt) == H.div[f"hreprt-Point", "hrepr-titled-v"](
        H.div["hrepr-title"]("Point"),
        H.div["hrepr-contents-v"](
            H.table["hrepr-instance-table"](
                H.tr(
                    H.td("x"),
                    H.td["hrepr-delimiter"]("="),
                    H.td(H.span["hreprt-int"]("1")),
                ),
                H.tr(
                    H.td("y"),
                    H.td["hrepr-delimiter"]("="),
                    H.td(H.span["hreprt-int"]("2")),
                ),
            )
        ),
    )

    assert hrepr(pt, max_depth=0) == H.span[
        f"hreprs-Point", "hrepr-short-instance"
    ](f"Point ...")


def test_tag():
    tg = H.span["hello"](1, 2, H.b("there"))
    assert hrepr(tg) is tg


def test_recursive():
    li = [1]
    li.append(li)

    assert hrepr(li) == H.div["hrepr-refbox"](
        H.span["hrepr-ref"]("#", 1, "="),
        H.div["hreprt-list", "hrepr-titled-h"](
            H.div["hrepr-title"]("["),
            H.div["hrepr-contents-h"](
                H.span["hreprt-int"]("1"),
                H.div["hrepr-refbox"](
                    H.span["hrepr-ref"]("⟳", 1, "="),
                    H.span["hreprs-list"]("[...]"),
                ),
            ),
            H.div["hrepr-title"]("]"),
        ),
    )


def test_unsupported():
    aa = hshort(Opaque())
    bb = H.span["hreprs-Opaque"]("<Opaque>")
    assert hshort(Opaque()) == H.span["hreprs-Opaque"]("<", "Opaque", ">")
