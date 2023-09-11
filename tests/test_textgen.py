# from hrepr.embed import js_embed
from hrepr.textgen import Context
from hrepr.textgen import Text as OldText
from hrepr.textgen_simple import Breakable, Sequence, Text
from tests.common import one_test_per_assert

# def test_max_col(file_regression):
#     dct = {
#         "module": "https://cdnjs.cloudflare.com/ajax/libs/cytoscape/3.23.0/cytoscape.esm.min.js",
#         "arguments": {
#             "elements": [
#                 {"data": {"id": "A"}},
#                 {"data": {"id": "B"}},
#                 {"data": {"id": "C"}},
#                 {"data": {"source": "A", "target": "B"}},
#                 {"data": {"source": "B", "target": "C"}},
#                 {"data": {"source": "C", "target": "A"}},
#             ],
#             "layout": {"name": "cose"},
#         },
#     }
#     file_regression.check(
#         str(
#             js_embed(dct).to_string(
#                 max_col=80, tabsize=4, offset=0, line_offset=0
#             )
#         )
#     )


def test_overflow_whitespace():
    ctx = Context(
        max_col=10, overflow="break", tabsize=0, offset=0, line_offset=0
    )
    t = OldText("hello                        ")
    val, offset = ctx.format(t)
    assert val == "hello     "


def test_overflow_backslash():
    ctx = Context(
        max_col=10, overflow="backslash", tabsize=0, offset=0, line_offset=0
    )
    t = OldText("woop dee doo woop")
    val, offset = ctx.format(t)
    assert val == "woop dee d\n\\ oo woop"


@one_test_per_assert
def test_empty():
    assert Text("").empty()
    assert not Text(" ").empty()
    assert not Text("x").empty()

    assert Breakable(start="", end="", body=[]).empty()
    assert not Breakable(start="(", end=")", body=[]).empty()

    assert Sequence().empty()
    assert not Sequence("x").empty()
