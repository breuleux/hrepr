from hrepr import H
from hrepr.std import standard_html as sht


def test_pair():
    p = H.pair["kls"](
        "red", "blue", delimiter=" -> ", stuff="xyz", type="color"
    )
    assert sht(p) == H.div["kls", "hreprt-color", "hrepr-pair"](
        "red", " -> ", "blue", stuff="xyz"
    )


def test_bracketed():
    brack = H.bracketed["kls"](
        H.pair("a", "b", delimiter=" -> "),
        H.pair("c", "d", delimiter=" <- "),
        "e",
        start="START",
        end="END",
        stuff="xyz",
    )

    assert sht(brack(vertical=True)) == H.div["kls", "hrepr-bracketed"](
        H.div["hrepr-open"]("START"),
        H.table["hrepr-body"](
            H.tr(H.td("a"), H.td["hrepr-delim"](" -> "), H.td("b"),),
            H.tr(H.td("c"), H.td["hrepr-delim"](" <- "), H.td("d"),),
            H.tr(H.td("e", colspan=3),),
        ),
        H.div["hrepr-close"]("END"),
        stuff="xyz",
    )

    assert sht(brack(horizontal=True)) == H.div["kls", "hrepr-bracketed"](
        H.div["hrepr-open"]("START"),
        H.div["hreprl-h", "hrepr-body"](
            H.div(H.div["hrepr-pair"]("a", " -> ", "b",)),
            H.div(H.div["hrepr-pair"]("c", " <- ", "d",)),
            H.div("e"),
        ),
        H.div["hrepr-close"]("END"),
        stuff="xyz",
    )


_reqjs = sht.initial_state["requirejs_resources"]


def test_javascript_tag():
    assert sht(H.javascript(export="blah", src="thing.js")) == H.script(
        'requirejs.config({paths: {blah: "thing.js?noext"}});'
    ).fill(resources=_reqjs)


def test_javascript_tag_2():
    assert sht(
        H.javascript("xxx='hello';", require="abc", export="xxx")
    ) == H.script(
        "define('xxx', ['abc'], (abc) => {",
        "xxx='hello';",
        "\nreturn xxx;});",
        "require(['xxx'], _ => {});",
    ).fill(
        resources=_reqjs
    )


def test_javascript_tag_lazy():
    assert sht(
        H.javascript("xxx='hello';", require="abc", export="xxx", lazy=True)
    ) == H.script(
        "define('xxx', ['abc'], (abc) => {",
        "xxx='hello';",
        "\nreturn xxx;});",
        "",
    ).fill(
        resources=_reqjs
    )


def test_javascript_tag_noexport():
    assert sht(H.javascript("xxx='hello';", require="abc")) == H.script(
        "require(['abc'], (abc) => {", "xxx='hello';", "});",
    ).fill(resources=_reqjs)


def test_interactive():
    assert sht(
        H.interactive(
            H.div["chapeau"](id="melon"),
            constructor="fou",
            options={"x": 1},
            export="everywhere",
        )
    ) == H.inline(
        H.div["chapeau"](id="melon"),
        sht(
            H.javascript(
                "let everywhere = fou(document.getElementById('melon'), {\"x\": 1});",
                require="fou",
                export="everywhere",
                lazy=False,
            )
        ),
    )


def test_interactive_2():
    sht(
        H.interactive(
            H.div["chapeau"](),
            constructor="fou",
            options={"x": 1},
            export="everywhere",
        )
    )
