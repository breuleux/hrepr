from itertools import count
from types import SimpleNamespace
from typing import Union

from ovld import ovld

from . import hjson
from .h import H, HType, Tag

_c = count()


ABSENT = object()


def _extract_as(transform, node, new_tag, **extract):
    ns = SimpleNamespace()
    extract["type"] = None
    for attr, dflt in extract.items():
        setattr(ns, attr, node.get_attribute(attr, dflt))
    attrs = {
        attr: value
        for attr, value in node.attributes.items()
        if attr not in extract
    }
    new_node = getattr(H, new_tag or node.name).fill(
        children=(),
        attributes={attr: transform(value) for attr, value in attrs.items()},
        resources=[transform(res) for res in node.resources],
    )
    if isinstance(ns.type, str):
        new_node = new_node[f"hreprt-{ns.type}"]
    return new_node, node.children, ns


# def _get_layout(ns, default="h"):
#     if ns.short:
#         return "s"
#     elif ns.horizontal:
#         return "h"
#     elif ns.vertical:
#         return "v"
#     else:
#         return default


# def _format_sequence(seq, layout):
#     if layout == "h" or layout == "s":
#         container = H.div[f"hreprl-{layout}", "hrepr-body"]
#         return container(*[H.div(x) for x in seq])
#     elif layout == "v":
#         table = H.table["hrepr-body"]()
#         for x in seq:
#             if isinstance(x, HType.pair):
#                 delimiter = x.get_attribute("delimiter", "")
#                 k, v = x.children
#                 row = H.tr(H.td(k), H.td["hrepr-delim"](delimiter), H.td(v))
#             else:
#                 row = H.tr(H.td(x, colspan=3))
#             table = table(row)
#         return table
#     else:  # pragma: no cover
#         raise ValueError(f"layout should be 'h' or 'v', not '{layout}'")


@ovld(
    initial_state={
        "requirejs_resources": [
            H.script(
                type="text/javascript",
                src="https://cdnjs.cloudflare.com/ajax/libs/require.js/2.3.6/require.min.js",
            )
        ],
        "hjson": hjson.dumps,
        "attribute_translators": {},
    }
)
def standard_html(self, node: Tag):
    """Generate standard HTML from non-standard tags generated by hrepr."""
    target, children, data = _extract_as(
        self, node, None, constructor=None, options=None, export=None, id=None
    )
    if data.constructor is not None:
        elemid = data.id or f"_hrepr_elem{next(_c)}"
        target = target(id=elemid)
        opts = self.hjson(data.options)
        code = f"new {data.constructor}(document.getElementById('{elemid}'), {opts});"

        if data.export:
            jsnode = H.javascript(
                f"let {data.export} = {code}", export=data.export,
            )
        else:
            jsnode = H.javascript(code)

        return H.inline(
            self(target(*children)),
            self(jsnode(require=data.constructor, lazy=False)),
        )

    else:

        def _default_translator(k, v):
            if (
                isinstance(v, str)
                or k == "class"
                or v is True
                or v is False
                or v is None
            ):
                return {k: v}
            else:
                return {k: self.hjson(v)}

        attributes = {}
        for k, v in node.attributes.items():
            translator = self.attribute_translators.get(k, _default_translator)
            attributes.update(translator(k, v))

        return type(node)(
            name=node.name,
            attributes=attributes,
            children=tuple(self(x) for x in node.children),
            resources=[self(res) for res in node.resources],
        )


# @ovld
# def standard_html(self, node: HType.ref):
#     _, children, data = _extract_as(self, node, "div", loop=False, num=-1)
#     sym = "⟳" if data.loop else "#"
#     ref = H.span["hrepr-ref"](sym, data.num)
#     if node.children:
#         return H.div["hrepr-refbox"](ref("="), *map(self, children))
#     else:
#         return ref


# @ovld
# def standard_html(self, node: HType.bracketed):
#     rval, children, data = _extract_as(
#         self,
#         node,
#         "div",
#         start="(",
#         end=")",
#         short=False,
#         horizontal=False,
#         vertical=False,
#     )
#     layout = _get_layout(data, "h")
#     body = _format_sequence(children, layout)
#     return self(
#         rval["hrepr-bracketed"](
#             H.div["hrepr-open"](data.start),
#             body,
#             H.div["hrepr-close"](data.end),
#         )
#     )


# @ovld
# def standard_html(self, node: HType.instance):
#     rval, children, data = _extract_as(
#         self, node, "div", short=False, horizontal=False, vertical=False,
#     )
#     layout = _get_layout(data, "h")
#     body = _format_sequence(children, layout)
#     return self(
#         rval["hrepr-instance", f"hreprl-{layout}"](
#             H.div["hrepr-title"](self(data.type)), body
#         )
#     )


# @ovld
# def standard_html(self, node: HType.pair):
#     rval, children, data = _extract_as(self, node, "div", delimiter="")
#     k, v = children
#     return self(rval["hrepr-pair"](k, data.delimiter, v))


# @ovld
# def standard_html(self, node: HType.atom):
#     rval, children, data = _extract_as(self, node, "span", value=ABSENT)
#     if data.value is not ABSENT:
#         rval = rval[f"hreprv-{data.value}"]
#     return self(rval(*children))


# @ovld
# def standard_html(self, node: HType.defn):
#     rval, children, _ = _extract_as(self, node, "span")
#     assert len(children) == 2
#     key, name = children
#     return self(
#         rval[f"hreprk-{key}"](
#             H.span["hrepr-defn-key"](key), " ", H.span["hrepr-defn-name"](name),
#         )
#     )


@ovld
def _parse_reqs(reqs: dict):
    return tuple(zip(*reqs.items()))


@ovld
def _parse_reqs(reqs: str):
    return [reqs], [reqs.split("/")[-1]]


@ovld
def _parse_reqs(reqs: Union[list, tuple, set, frozenset]):
    reqs = list(reqs)
    return reqs, [r.split("/")[-1] for r in reqs]


@ovld
def standard_html(self, node: HType.javascript):
    rval, children, data = _extract_as(
        self, node, "script", require=None, export=None, src=None, lazy=False
    )

    src = data.src
    if src is not None:
        assert not children
        assert not data.require
        assert data.export is not None
        if src.endswith(".js"):
            src += "?noext"
        rval = rval(
            f'requirejs.config({{paths: {{"{data.export}": "{src}"}}}});'
        )
        return rval.fill(resources=self.requirejs_resources)

    else:
        reqs, reqargs = _parse_reqs(data.require)
        reqs = str(list(reqs))
        reqargs = ", ".join(reqargs)
        if data.export is not None:
            children = [
                f"define('{data.export}', {reqs}, ({reqargs}) => {{",
                *children,
                f"\nreturn {data.export};}});",
                "" if data.lazy else f"require(['{data.export}'], _ => {{}});",
            ]
        else:
            assert not data.lazy
            children = [
                f"require({reqs}, ({reqargs}) => {{",
                *children,
                "});",
            ]
        return rval(*children).fill(resources=self.requirejs_resources)


@ovld
def standard_html(self, node: HType.include):
    _, children, data = _extract_as(self, node, "include", path=None, type=None)
    if data.type is None or data.path is None:
        raise TypeError("H.include must have a type and a path")

    if data.type == "text/css":
        return H.style(open(data.path).read())
    elif data.type == "text/javascript":
        return H.script(open(data.path).read())
    else:
        raise TypeError(f"Cannot include type '{data.type}'")


@ovld
def standard_html(self, node: object):
    return node
