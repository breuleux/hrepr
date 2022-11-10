from hrepr.textgen import Context, Text


def test_overflow_whitespace():
    ctx = Context(
        max_col=10, overflow="break", tabsize=0, offset=0, line_offset=0
    )
    t = Text("hello                        ")
    val, offset = ctx.format(t)
    assert val == "hello     "
