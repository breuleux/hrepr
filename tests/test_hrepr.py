import dataclasses
import re
from dataclasses import dataclass

from hrepr import H
from hrepr import hrepr as real_hrepr
from hrepr.h import styledir

css_hrepr = open(f"{styledir}/hrepr.css", encoding="utf-8").read()
hrepr = real_hrepr.variant(fill_resources=False)


@dataclass
class Point:
    x: int
    y: int

    def some_method(self):
        pass


class Opaque:
    pass


def hshort(x, **kw):
    return hrepr(x, max_depth=0, **kw)


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
        obj=re.sub(pattern=r"at 0x[0-9a-f]+", string=repr(obj), repl="XXX"),
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


def maxlen(i):
    def _(obj, file_regression):
        check_hrepr(
            file_regression,
            description=f"hrepr(obj, sequence_max={i})",
            obj=repr(obj),
            result=hrepr(obj, sequence_max=i),
        )

    _.__name__ = f"maxlen{i}"
    return _


def string_cutoff(i):
    def _(obj, file_regression):
        check_hrepr(
            file_regression,
            description=f"hrepr(obj, string_cutoff={i})",
            obj=repr(obj),
            result=hrepr(obj, string_cutoff=i, max_depth=0),
        )

    _.__name__ = f"string_cutoff{i}"
    return _


factory.true(True, standard)
factory.false(False, standard)
factory.none(None, standard)

factory.int(123, standard)
factory.float(1.25, standard)

factory.str("hello", standard)
factory.spaces("3   spaces", standard)
factory.sentence(
    "hello this is a bit long",
    standard,
    depth(0),
    string_cutoff(10),
    string_cutoff(5),
    string_cutoff(10000),
)

factory.bytes(b"hello", standard)
factory.bsentence(b"hello this is a bit long", standard, depth(0))

factory.tuple0((), standard)
factory.tuple1((1,), standard)
factory.tuple2((11, 22), standard, depth(0))
factory.list([1, 2, 3], standard)
factory.biglist(list(range(1000)), standard, depth(0))
factory.set({11, 22}, standard, depth(0))
factory.frozenset(frozenset({11, 22, 33}), standard, depth(0))
factory.dict0({}, standard)
factory.dict({"a": 1, "b": 2, "c": 3}, standard)
factory.dict_keys({"a": 1, "b": 2, "c": 3}.keys(), standard, depth(0))
factory.dict_values({"a": 1, "b": 2, "c": 3}.values(), standard, depth(0))
factory.dataclass(Point(1, 2), standard, depth(0))
factory.unknown(Opaque, standard)

factory.list10(
    list(range(10)), maxlen(5), maxlen(0), maxlen(1), maxlen(-1), maxlen(10)
)
factory.set10(set(range(10)), maxlen(5))
factory.dict10(dict((i, i * i) for i in range(10)), maxlen(5))

factory.exception(TypeError("oh no!"), standard)


def _gen(x):
    yield x


async def _coro(x):
    pass


async def _corogen(x):
    yield x


factory.misc(
    {
        "functions": [hshort, Point.some_method, (lambda x: x)],
        "generators": [_gen(3)],
        "coroutines": [_coro(3), _corogen(3)],
        "classes": [Point, Exception, type],
        "builtins": [pow, open, [].append],
        "wrappers": [dict.update, list.__str__],
        "methods": [Point(1, 2).some_method, [].__str__],
        "modules": [dataclasses],
    },
    standard,
)

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
