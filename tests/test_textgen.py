import dataclasses

from hrepr import H, pstr, trepr
from hrepr.term import standard_terminal
from hrepr.textgen import Context, Text

from .common import one_test_per_assert


def trepr_s(x, **kw):
    return str(trepr(x, **kw))


def trepr_f(x, **kw):
    return trepr(x).to_string(**kw)


def indents(s):
    return [len(line) - len(line.lstrip()) for line in s.split("\n")]


def lengths(s):
    return [len(line) for line in s.split("\n")]


@dataclasses.dataclass
class Point:
    x: int
    y: int

    def some_method(self):
        pass


@one_test_per_assert
def test_trepr():
    assert pstr([1, 2, "hello"]) == "[1, 2, 'hello']"
    assert pstr({"a": 1, "b": 2}) == "{'a': 1, 'b': 2}"
    assert pstr(Point(1, 2)) == "Point(x=1, y=2)"
    assert (
        pstr(H.span["kls"](H.b("great"), "canyon"))
        == '<span class="kls"><b>great</b>canyon</span>'
    )


def _gen(x):
    yield x


async def _coro(x):
    pass


async def _corogen(x):
    yield x


@one_test_per_assert
def test_trepr_functions():
    # Functions
    assert pstr(lengths) == "function lengths"
    assert pstr(Point.some_method) == "function some_method"
    assert pstr(lambda x: x) == "function <lambda>"
    # Generators
    assert pstr(_gen(3)) == "generator _gen"
    # Coroutines
    assert pstr(_coro(3)) == "coroutine _coro"
    assert pstr(_corogen(3)) == "async_generator _corogen"
    # Classes
    assert pstr(Point) == "class Point"
    assert pstr(Exception) == "class Exception"
    assert pstr(type) == "metaclass type"
    # Builtins
    assert pstr(pow) == "builtin pow"
    assert pstr(open) == "builtin io.open"
    assert pstr([].append) == "builtin <list>.append"
    # Wrappers/Descriptors
    assert pstr(dict.update) == "descriptor dict.update"
    assert pstr(list.__str__) == "descriptor object.__str__"
    # Methods
    assert pstr(Point(1, 2).some_method) == "method <Point>.some_method"
    assert pstr([].__str__) == "method <list>.__str__"
    # Modules
    assert pstr(dataclasses) == "module dataclasses"


def test_trepr_exception():
    assert pstr(TypeError("BAH")) == "TypeError(BAH)"


def test_recursive():
    li = [1, 2]
    li.append(li)
    assert pstr(li) == "#1=[1, 2, #1=[...]]"
    assert pstr(li, shortrefs=True) == "#1=[1, 2, #1]"


def test_indent():
    for indent in [3, 4]:
        i = "\n" + indent * " "
        assert (
            pstr([1, 2, 3, 4], max_col=10, indent=indent)
            == f"[{i}1, {i}2, {i}3, {i}4\n]"
        )


# Note: there are spaces after the commas
_expected = """[
    1, 
    {
        'a': 2, 
        'b': 3
    }, 
    4
]"""  # noqa: W291


def test_nested_indent():
    result = pstr([1, {"a": 2, "b": 3}, 4], max_col=15, indent=4)
    assert indents(result) == [0, 4, 4, 8, 8, 4, 4, 0]
    assert result == _expected


def test_max_indent():
    data = [[[[[["hello"]]]]]]
    result = pstr(data, indent=2, max_col=10, max_indent=6)
    assert indents(result) == [0, 2, 4, 6, 6, 6, 6, 6, 6, 6, 4, 2, 0]


def test_overflow():
    phrase = "the healthy fox jumps over the fancy shrub or whatever I don't remember"
    data = [phrase]

    s = pstr(data, max_col=30, overflow="allow")
    assert indents(s) == [0, 4, 0]
    assert lengths(s) == [1, 77, 1]
    assert sum(lengths(s)) - sum(indents(s)) == len(phrase) + 4

    s = pstr(data, max_col=30, overflow="break")
    assert indents(s) == [0, 4, 4, 4, 0]
    assert lengths(s) == [1, 30, 30, 25, 1]
    assert sum(lengths(s)) - sum(indents(s)) == len(phrase) + 4

    s = pstr(data, max_col=30, overflow="backslash")
    assert indents(s) == [0, 4, 4, 4, 0]
    assert lengths(s) == [1, 30, 30, 29, 1]
    assert sum(lengths(s)) - sum(indents(s)) == len(phrase) + 4 + 4


def test_overflow_whitespace():
    ctx = Context(
        max_col=10, overflow="break", tabsize=0, offset=0, line_offset=0
    )
    t = Text("hello                        ")
    val, offset = ctx.format(t)
    assert val == "hello     "


def test_variant_hclass():
    from hrepr import Hrepr

    obj = {"a": [1, 2, 3], "b": 4}
    assert str(trepr.variant(hclass=Hrepr)(obj)) == "<dict>"


def test_variant_backend():
    from hrepr import hrepr

    obj = {"a": [1, 2, 3], "b": 4}
    assert str(trepr(obj)) == str(hrepr.variant(backend=standard_terminal)(obj))


def test_variant_no_refinject():
    li = [1, 2]
    obj = [li, li]
    assert trepr_s(obj) == "[#1=[1, 2], #1=[...]]"
    assert (
        str(trepr.variant(inject_references=False)(obj)) == "[[1, 2], #1=[...]]"
    )
