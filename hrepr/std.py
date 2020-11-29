from itertools import count
from types import SimpleNamespace

from ovld import ovld

from .h import H, Tag

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
    new_node = getattr(H, new_tag).fill(
        children=(),
        attributes={attr: transform(value) for attr, value in attrs.items()},
        resources=[transform(res) for res in node.resources],
    )
    if isinstance(ns.type, str):
        new_node = new_node[f"hreprt-{ns.type}"]
    return new_node, node.children, ns


def _get_layout(ns, default="h"):
    if ns.short:
        return "s"
    elif ns.horizontal:
        return "h"
    elif ns.vertical:
        return "v"
    else:
        return default


def _format_sequence(fn, seq, layout):
    if layout == "h" or layout == "s":
        container = H.div[f"hreprl-{layout}", "hrepr-body"]
        return container(*[H.div(fn(x)) for x in seq])
    elif layout == "v":
        table = H.table["hrepr-body"]()
        for x in seq:
            if isinstance(x, type(H.pair)):
                delimiter = x.get_attribute("delimiter", "")
                k, v = x.children
                row = H.tr(
                    H.td(fn(k)), H.td["hrepr-delim"](delimiter), H.td(fn(v))
                )
            else:
                row = H.tr(H.td(fn(x), colspan=3))
            table = table(row)
        return table
    else:  # pragma: no cover
        raise ValueError(f"layout should be 'h' or 'v', not '{layout}'")


@ovld
def standard_html(self, node: Tag):
    """Generate standard HTML from non-standard tags generated by hrepr."""
    return type(node)(
        name=node.name,
        attributes={k: self(v) for k, v in node.attributes.items()},
        children=tuple(self(x) for x in node.children),
        resources=[self(res) for res in node.resources],
    )


@ovld
def standard_html(self, node: type(H.ref)):
    _, children, data = _extract_as(self, node, "div", loop=False, num=-1)
    sym = "⟳" if data.loop else "#"
    ref = H.span["hrepr-ref"](sym, data.num)
    if node.children:
        return H.div["hrepr-refbox"](ref("="), *map(self, children))
    else:
        return ref


@ovld
def standard_html(self, node: type(H.bracketed)):
    rval, children, data = _extract_as(
        self,
        node,
        "div",
        start="(",
        end=")",
        short=False,
        horizontal=False,
        vertical=False,
    )
    layout = _get_layout(data, "h")
    body = _format_sequence(self, children, layout)
    return rval["hrepr-bracketed"](
        H.div["hrepr-open"](data.start), body, H.div["hrepr-close"](data.end)
    )


@ovld
def standard_html(self, node: type(H.instance)):
    rval, children, data = _extract_as(
        self, node, "div", short=False, horizontal=False, vertical=False,
    )
    layout = _get_layout(data, "h")
    body = _format_sequence(self, children, layout)
    return rval["hrepr-instance", f"hreprl-{layout}"](
        H.div["hrepr-title"](self(data.type)), body
    )


@ovld
def standard_html(self, node: type(H.pair)):
    rval, children, data = _extract_as(self, node, "div", delimiter="")
    k, v = children
    return rval["hrepr-pair"](self(k), data.delimiter, self(v))


@ovld
def standard_html(self, node: type(H.atom)):
    rval, children, data = _extract_as(self, node, "span", value=ABSENT)
    if data.value is not ABSENT:
        rval = rval[f"hreprv-{data.value}"]
    return rval(*children)


@ovld
def standard_html(self, node: type(H.require)):
    rval, children, data = _extract_as(
        self, node, "script", src=None, name=None
    )
    assert not children
    rval = rval(f'requirejs.config({{paths: {{{data.name}: "{data.src}"}}}});')
    return rval.fill(
        resources=H.script(
            type="text/javascript",
            src="https://cdnjs.cloudflare.com/ajax/libs/require.js/2.3.6/require.min.js",
        )
    )


@ovld
def standard_html(self, node: type(H.script)):
    rval, children, data = _extract_as(
        self, node, "script", require=None, create_div=None
    )

    if children:
        if data.create_div is not None:
            divname = f"_hrepr_{next(_c)}"
            children = [
                "(function () {",
                f"let {data.create_div} = document.getElementById('{divname}');",
                *children,
                "})();",
            ]

        if data.require is not None:
            reqs = (
                list(data.require)
                if isinstance(data.require, (list, tuple))
                else [data.require]
            )
            reqargs = ", ".join(reqs)
            children = [
                f"require({reqs}, function ({reqargs}) {{",
                *children,
                "});",
            ]

        rval = rval(*children)
        if data.create_div is not None:
            rval = H.inline(H.div(id=divname), rval)

        return rval

    else:
        return rval


@ovld
def standard_html(self, node: object):
    return node
