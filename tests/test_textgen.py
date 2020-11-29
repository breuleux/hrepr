from dataclasses import dataclass

from hrepr import H, pstr, trepr
from hrepr.textgen import Context, Text


def trepr_s(x, **kw):
    return str(trepr(x, **kw))


def trepr_f(x, **kw):
    return trepr(x).to_string(**kw)


def indents(s):
    return [len(line) - len(line.lstrip()) for line in s.split("\n")]


def lengths(s):
    return [len(line) for line in s.split("\n")]


@dataclass
class Point:
    x: int
    y: int


def test_trepr():
    assert pstr([1, 2, "hello"]) == "[1, 2, 'hello']"
    assert pstr({"a": 1, "b": 2}) == "{'a': 1, 'b': 2}"
    assert pstr(Point(1, 2)) == "Point(x=1, y=2)"
    assert (
        pstr(H.span["kls"](H.b("great"), "canyon"))
        == '<span class="kls"><b>great</b>canyon</span>'
    )


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
