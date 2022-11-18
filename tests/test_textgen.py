from hrepr.embed import js_embed
from hrepr.textgen import Context, Text


def test_max_col(file_regression):
    dct = {
        "module": "https://cdnjs.cloudflare.com/ajax/libs/cytoscape/3.23.0/cytoscape.esm.min.js",
        "arguments": {
            "elements": [
                {"data": {"id": "A"}},
                {"data": {"id": "B"}},
                {"data": {"id": "C"}},
                {"data": {"source": "A", "target": "B"}},
                {"data": {"source": "B", "target": "C"}},
                {"data": {"source": "C", "target": "A"}},
            ],
            "layout": {"name": "cose"},
        },
    }
    file_regression.check(
        str(
            js_embed(dct).to_string(
                max_col=80, tabsize=4, offset=0, line_offset=0
            )
        )
    )


def test_overflow_whitespace():
    ctx = Context(
        max_col=10, overflow="break", tabsize=0, offset=0, line_offset=0
    )
    t = Text("hello                        ")
    val, offset = ctx.format(t)
    assert val == "hello     "


def test_overflow_backslash():
    ctx = Context(
        max_col=10, overflow="backslash", tabsize=0, offset=0, line_offset=0
    )
    t = Text("woop dee doo woop")
    val, offset = ctx.format(t)
    assert val == "woop dee d\n\\ oo woop"
