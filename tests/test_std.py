# import os

# from hrepr import H
# from hrepr.std import standard_html as sht

# here = os.path.dirname(__file__)


# # def gentest(f):
# #     def _(file_regression):
# #         file_regression.check(str(sht(f())), extension=".html")

# #     _.__name__ = f.__name__
# #     return _


# # @gentest
# # def test_brack():
# #     return H.bracketed["kls"](
# #         H.pair("a", "b", delimiter=" -> "),
# #         H.pair("c", "d", delimiter=" <- "),
# #         "e",
# #         start="START",
# #         end="END",
# #         stuff="xyz",
# #     )


# # def test_pair():
# #     p = H.pair["kls"](
# #         "red", "blue", delimiter=" -> ", stuff="xyz", type="color"
# #     )
# #     assert sht(p) == H.div["kls", "hreprt-color", "hrepr-pair"](
# #         "red", " -> ", "blue", stuff="xyz"
# #     )


# # def test_bracketed():
# #     brack = H.bracketed["kls"](
# #         H.pair("a", "b", delimiter=" -> "),
# #         H.pair("c", "d", delimiter=" <- "),
# #         "e",
# #         start="START",
# #         end="END",
# #         stuff="xyz",
# #     )

# #     assert sht(brack(vertical=True)) == H.div["kls", "hrepr-bracketed"](
# #         H.div["hrepr-open"]("START"),
# #         H.table["hrepr-body"](
# #             H.tr(H.td("a"), H.td["hrepr-delim"](" -> "), H.td("b"),),
# #             H.tr(H.td("c"), H.td["hrepr-delim"](" <- "), H.td("d"),),
# #             H.tr(H.td("e", colspan="3"),),
# #         ),
# #         H.div["hrepr-close"]("END"),
# #         stuff="xyz",
# #     )

# #     assert sht(brack(horizontal=True)) == H.div["kls", "hrepr-bracketed"](
# #         H.div["hrepr-open"]("START"),
# #         H.div["hreprl-h", "hrepr-body"](
# #             H.div(H.div["hrepr-pair"]("a", " -> ", "b",)),
# #             H.div(H.div["hrepr-pair"]("c", " <- ", "d",)),
# #             H.div("e"),
# #         ),
# #         H.div["hrepr-close"]("END"),
# #         stuff="xyz",
# #     )


# _reqjs = sht.initial_state["requirejs_resources"]


# def test_javascript_tag():
#     assert sht(H.javascript(export="blah", src="thing.js")) == H.script(
#         'requirejs.config({paths: {"blah": "thing.js?noext"}});'
#     ).fill(resources=_reqjs)


# def test_javascript_tag_2():
#     assert sht(
#         H.javascript("xxx='hello';", require="abc", export="xxx")
#     ) == H.script(
#         "define('xxx', ['abc'], (abc) => {",
#         "xxx='hello';",
#         "\nreturn xxx;});",
#         "require(['xxx'], _ => {});",
#     ).fill(
#         resources=_reqjs
#     )


# def test_javascript_tag_req_list():
#     assert sht(
#         H.javascript("xxx='hello';", require=["abc", "d/ef"], export="xxx")
#     ) == H.script(
#         "define('xxx', ['abc', 'd/ef'], (abc, ef) => {",
#         "xxx='hello';",
#         "\nreturn xxx;});",
#         "require(['xxx'], _ => {});",
#     ).fill(
#         resources=_reqjs
#     )


# def test_javascript_tag_req_dict():
#     assert sht(
#         H.javascript(
#             "xxx='hello';", require={"abc": "A", "d/ef": "B"}, export="xxx"
#         )
#     ) == H.script(
#         "define('xxx', ['abc', 'd/ef'], (A, B) => {",
#         "xxx='hello';",
#         "\nreturn xxx;});",
#         "require(['xxx'], _ => {});",
#     ).fill(
#         resources=_reqjs
#     )


# def test_javascript_tag_lazy():
#     assert sht(
#         H.javascript("xxx='hello';", require="abc", export="xxx", lazy=True)
#     ) == H.script(
#         "define('xxx', ['abc'], (abc) => {",
#         "xxx='hello';",
#         "\nreturn xxx;});",
#         "",
#     ).fill(
#         resources=_reqjs
#     )


# def test_javascript_tag_noexport():
#     assert sht(H.javascript("xxx='hello';", require="abc")) == H.script(
#         "require(['abc'], (abc) => {", "xxx='hello';", "});",
#     ).fill(resources=_reqjs)


# def test_constructed_element():
#     assert sht(
#         H.div["chapeau"](id="melon", constructor="fou", options={"x": 1},)
#     ) == H.inline(
#         H.div["chapeau"](id="melon"),
#         sht(
#             H.javascript(
#                 "new fou(document.getElementById('melon'), {\"x\": 1});",
#                 require="fou",
#                 lazy=False,
#             )
#         ),
#     )


# def test_constructed_element_export():
#     assert sht(
#         H.div["chapeau"](
#             id="melon",
#             constructor="fou",
#             options={"x": 1},
#             export="everywhere",
#         )
#     ) == H.inline(
#         H.div["chapeau"](id="melon"),
#         sht(
#             H.javascript(
#                 "let everywhere = new fou(document.getElementById('melon'), {\"x\": 1});",
#                 require="fou",
#                 export="everywhere",
#                 lazy=False,
#             )
#         ),
#     )


# # def test_constructed_special_element():
# #     assert sht(
# #         H.atom(
# #             id="melon",
# #             type="cool",
# #             constructor="fou",
# #             options={"x": 1},
# #             export="everywhere",
# #         )
# #     ) == H.inline(
# #         H.span["hreprt-cool"](id="melon"),
# #         sht(
# #             H.javascript(
# #                 "let everywhere = new fou(document.getElementById('melon'), {\"x\": 1});",
# #                 require="fou",
# #                 export="everywhere",
# #                 lazy=False,
# #             )
# #         ),
# #     )


# # def test_include_js():
# #     assert sht(
# #         H.include(path=os.path.join(here, "x.js"), type="text/javascript")
# #     ) == H.script("function hello(x) { return x * x; }\n")


# # def test_include_css():
# #     assert sht(
# #         H.include(path=os.path.join(here, "x.css"), type="text/css")
# #     ) == H.style(".hello { color: red; }\n")


# # def test_include_notype():
# #     with pytest.raises(TypeError):
# #         sht(H.include(path=os.path.join(here, "x.css"),))


# # def test_include_badtype():
# #     with pytest.raises(TypeError):
# #         sht(H.include(path=os.path.join(here, "x.css"), type="text/whatever"))


# def test_variant():
#     def x_attribute(k, v):
#         return {"y": v * 2}

#     sht2 = sht.copy(initial_state={"attribute_translators": {"x": x_attribute}})
#     assert sht2(H.div("oh!", x="hello", z="zebra")) == H.div(
#         "oh!", y="hellohello", z="zebra"
#     )
