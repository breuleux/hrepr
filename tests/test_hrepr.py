from dataclasses import dataclass

import pytest

from hrepr import H
from hrepr import hrepr as real_hrepr
from hrepr.h import styledir

from .common import one_test_per_assert

css_hrepr = open(f"{styledir}/hrepr.css", encoding="utf-8").read()
hrepr = real_hrepr.variant(fill_resources=False)


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
    assert hrepr("3   spaces") == H.span["hreprt-str"]("3   spaces")
    assert hrepr("hello this is a bit long") == H.span["hreprt-str"](
        "hello this is a bit long"
    )
    assert hshort("hello this is a bit long") == H.span["hreprt-str"](
        "hello this is a b..."
    )
    assert hshort("hello this is a bit long", string_cutoff=10) == H.span[
        "hreprt-str"
    ]("hello t...")
    assert hshort("hello this is a bit long", string_cutoff=5) == H.span[
        "hreprt-str"
    ]("he...")
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


def test_function():
    assert hrepr(Opaque) == H.span["hreprk-class"](
        H.span["hrepr-defn-key"]("class"),
        " ",
        H.span["hrepr-defn-name"]("Opaque"),
    )


def check_hrepr(file_regression, **sections):
    utf8 = H.meta(
        {"http-equiv": "Content-type"}, content="text/html", charset="UTF-8"
    )
    page = H.inline(
        H.raw("<!DOCTYPE html>"),
        H.html(
            H.head(utf8, H.style(css_hrepr)),
            H.body(
                H.inline(H.h2(k), H.pre(v) if isinstance(v, str) else v,)
                for k, v in sections.items()
            ),
        ),
    )
    file_regression.check(str(page), extension=".html")


class Check:
    def __init__(self, test_name):
        self.test_name = test_name

    def create_single_test(self, obj, test):
        def _(file_regression):
            test(obj, file_regression)

        name = _.__name__ = f"{self.test_name}[{test.__name__}]"
        globals()[name] = _

    def __getattr__(self, attr):
        return Check(test_name=f"test_{attr}")

    def __call__(self, obj, *tests):
        assert self.test_name

        for t in tests:
            self.create_single_test(obj, t)


factory = Check(None)


def standard(obj, file_regression):
    check_hrepr(
        file_regression,
        description="hrepr(obj)",
        obj=repr(obj),
        result=hrepr(obj),
    )


def shortrefs(obj, file_regression):
    check_hrepr(
        file_regression,
        description="hrepr(obj, shortrefs=True)",
        obj=repr(obj),
        result=hrepr(obj, shortrefs=True),
    )


def depth(i):
    def _(obj, file_regression):
        check_hrepr(
            file_regression,
            description=f"hrepr(obj, max_depth={i})",
            obj=repr(obj),
            result=hrepr(obj, max_depth=i),
        )

    _.__name__ = f"depth{i}"
    return _


factory.tuple0((), standard)
factory.tuple1((1,), standard)
factory.tuple2((11, 22), standard)
factory.list([1, 2, 3], standard)
factory.set({11, 22}, standard)
factory.frozenset(frozenset({11, 22, 33}), standard)
factory.dict0({}, standard)
factory.dict({"a": 1, "b": 2, "c": 3}, standard)

factory.biglist(list(range(1000)), standard, depth(0))
factory.dataclass(Point(1, 2), standard, depth(0))

factory.deep(
    {
        "apple": [1, [[2]]],
        "banana": [7, (8, 9)],
        "cherry": {str: "fire", int: "forest", Point: Point(3, 4)},
    },
    standard,
    depth(0),
    depth(1),
    depth(2),
)

factory.multiref([[1, 2]] * 2, standard, shortrefs)


def _recursive():
    li = [1]
    li.append(li)
    return li


factory.recursive(_recursive(), standard, shortrefs)
factory.recursive2([_recursive()] * 2, standard, shortrefs)


def test_tag():
    tg = H.span["hello"](1, 2, H.b("there"))
    assert hrepr(tg) == tg


def test_unsupported():
    assert hshort(Opaque()) == H.span["hreprt-Opaque"](
        "<", "tests.test_hrepr.Opaque", ">"
    )


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
        "newclass", "hreprt-int"
    ]("1")
