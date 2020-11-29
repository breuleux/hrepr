from hrepr import H
from hrepr.std import standard_html as sht


def test_pair():
    p = H.pair["kls"](
        "red", "blue", delimiter=" -> ", stuff="xyz", type="color"
    )
    assert sht(p) == H.div["hrepr-pair", "hreprt-color", "kls"](
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

    assert sht(brack(vertical=True)) == H.div["hrepr-bracketed", "kls"](
        H.div["hrepr-open"]("START"),
        H.table["hrepr-body"](
            H.tr(H.td("a"), H.td["hrepr-delim"](" -> "), H.td("b"),),
            H.tr(H.td("c"), H.td["hrepr-delim"](" <- "), H.td("d"),),
            H.tr(H.td("e", colspan=3),),
        ),
        H.div["hrepr-close"]("END"),
        stuff="xyz",
    )

    assert sht(brack(horizontal=True)) == H.div["hrepr-bracketed", "kls"](
        H.div["hrepr-open"]("START"),
        H.div["hrepr-body", "hreprl-h"](
            H.div(H.div["hrepr-pair"]("a", " -> ", "b",)),
            H.div(H.div["hrepr-pair"]("c", " <- ", "d",)),
            H.div("e"),
        ),
        H.div["hrepr-close"]("END"),
        stuff="xyz",
    )


def test_require():
    assert sht(H.require(name="blah", src="thing")) == H.script(
        'requirejs.config({paths: {blah: "thing"}});'
    ).fill(
        resources=H.script(
            type="text/javascript",
            src="https://cdnjs.cloudflare.com/ajax/libs/require.js/2.3.6/require.min.js",
        )
    )


def test_script():
    from hrepr.std import _c

    cnt = next(_c)
    divname = f"_hrepr_{cnt + 1}"
    one = sht(
        H.script("code;", require=["apple", "banana"], create_div="divvo")
    )
    two = H.inline(
        H.div(id=divname),
        H.script(
            "require(['apple', 'banana'], function (apple, banana) {",
            "(function () {",
            f"let divvo = document.getElementById('{divname}');",
            "code;",
            "})();",
            "});",
        ),
    )
    assert one == two


def test_script_empty():
    s = H.script(src="blah")
    assert sht(s) == s
