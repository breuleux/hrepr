import json
import re
from dataclasses import dataclass
from html import escape
from pathlib import Path
from typing import Union

from ovld import OvldMC

from . import resource
from .h import H, Tag, gensym
from .j import Code, Into, J, Module, Script
from .textgen_simple import (
    Breakable,
    Sequence,
    Text,
    TextFormatter,
    collect_resources,
    join,
)

constructor_lib = H.script((Path(__file__).parent / "hlib.js").read_text())


class ResourceDeduplicator:
    def __init__(self):
        self.seen_resources = set()

    def __call__(self, resource):
        if resource in self.seen_resources:
            return False
        else:
            self.seen_resources.add(resource)
            return True


def no_resources(resource):  # pragma: no cover
    return False


@dataclass
class Workspace:
    __slots__ = (
        "open",
        "close",
        "attributes",
        "children",
        "resources",
        "extra",
        "escape_children",
    )

    open: str
    close: str
    attributes: dict
    children: list
    resources: list
    extra: list
    escape_children: bool


class HTMLGenerator(metaclass=OvldMC):
    #############
    # Utilities #
    #############

    def _text_parts(self, workspace):
        def convert_child(c):
            if isinstance(c, TextFormatter):
                return c
            elif isinstance(c, str):
                if workspace.escape_children:
                    return escape(str(c))
                else:
                    return c
            else:
                return self._text_parts(c)

        attr = "".join(
            f" {k}" if v is True else f' {k}="{escape(v)}"'
            for k, v in workspace.attributes.items()
        )

        children = list(map(convert_child, workspace.children))

        if workspace.open:
            if workspace.close:
                return Breakable(
                    start=f"<{workspace.open}{attr}>",
                    body=children,
                    end=f"</{workspace.open}>",
                )
            else:
                assert not children
                return Text(f"<{workspace.open}{attr} />")
        else:
            return Breakable(start=None, body=children, end=None)

    def expand_resources(self, value, embed):
        def sub(m):
            res = resource.registry.resolve(int(m.groups()[0]))
            return self.expand_resources(embed(res.obj), embed)

        return re.sub(
            pattern=rf"\[{resource.embed_key}:([0-9]+)\]",
            string=str(value),
            repl=sub,
        )

    ##############
    # Tags rules #
    ##############

    def _tag_default(self, node, workspace):
        workspace.open = node.name
        workspace.close = node.name

    def _tag_void(self, node, workspace):
        assert not workspace.children
        workspace.open = node.name
        workspace.close = None

    tagrule_area = _tag_void
    tagrule_base = _tag_void
    tagrule_br = _tag_void
    tagrule_col = _tag_void
    tagrule_command = _tag_void
    tagrule_embed = _tag_void
    tagrule_hr = _tag_void
    tagrule_img = _tag_void
    tagrule_input = _tag_void
    tagrule_keygen = _tag_void
    tagrule_link = _tag_void
    tagrule_meta = _tag_void
    tagrule_param = _tag_void
    tagrule_source = _tag_void
    tagrule_track = _tag_void
    tagrule_wbr = _tag_void
    tagrule_doctype = _tag_void

    def tagrule_script(self, node, workspace):
        workspace.escape_children = False
        new_children = []
        for child in workspace.children:
            assert isinstance(child, str)
            new_children.append(self.expand_resources(child, self.js_embed))
        workspace.children = new_children
        return self._tag_default(node, workspace)

    def tagrule_style(self, node, workspace):
        workspace.escape_children = False
        return self._tag_default(node, workspace)

    def tagrule_inline(self, node, workspace):
        return

    def tagrule_raw(self, node, workspace):
        workspace.escape_children = False

    #####################
    # node_embed method #
    #####################

    def node_embed(self, node: Union[str, TextFormatter]):
        return node

    def node_embed(self, node: object):
        if hasattr(node, "__h__"):
            return self.node_embed(node.__h__())
        else:
            return str(node)

    def node_embed(self, node: J):
        embedded = self.js_embed(node)
        resources = collect_resources(embedded, [])

        lines = [
            f"const obj = {embedded};",
            "$$INTO.__object.__resolve(obj);",
        ]

        element = None

        for r in [r for r in resources if isinstance(r, Into)]:
            assert element is None
            element = r.element.autoid()
            replace_line = ""

        if element is None:
            element = H.placeholder().autoid()
            replace_line = "obj && $$INTO.replaceWith(obj);"

        workspace = self.node_embed(element)
        wid = element.attributes["id"]

        lines = [*lines, replace_line]

        scripts = {r.src for r in resources if isinstance(r, Script)}
        lines = [
            f"$$HREPR.loadScripts({self.js_embed(list(scripts))},()=>{{",
            *lines,
            "});",
        ]

        into_line = f"const $$INTO = $$HREPR.prepare({self.js_embed(wid)});"
        lines = [into_line, *lines]

        for r in [r for r in resources if isinstance(r, Module)]:
            if r.symbol:
                line = f"import {{ {r.symbol} as {r.varname} }} from {self.js_embed(r.module)};"
            else:
                line = f"import {r.varname} from {self.js_embed(r.module)};"
            lines = [line, *lines]

        script = H.script("\n".join(lines), type="module")

        for co in [r for r in resources if isinstance(r, Code)]:
            assert co.code
            workspace.resources.append(H.script(co.code))

        for tag in [r for r in resources if isinstance(r, Tag)]:
            workspace.resources.append(tag)

        workspace.resources.append(constructor_lib)
        workspace.extra.append(script)
        return workspace

    def node_embed(self, node: Tag):
        workspace = Workspace(
            open=None,
            close=None,
            attributes={},
            children=[],
            resources=list(node.resources),
            extra=[],
            escape_children=True,
        )

        workspace.children = [self.node_embed(child) for child in node.children]
        for child in workspace.children:
            if getattr(child, "extra", None):
                workspace.extra += child.extra
                child.extra = []
            if getattr(child, "resources", None):
                workspace.resources += child.resources
                child.resources = []

        node_name = (node.name or "inline").replace("!", "").lower()
        tag_rule = (
            getattr(self, f"tagrule_{node_name}", None) or self._tag_default
        )
        if tag_rule(node, workspace) is False:  # pragma: no cover
            pass
        else:
            for k, v in node.attributes.items():
                rule = getattr(self, f"attrrule_{k}", None)
                if rule is None:
                    new_value = self.attr_embed(v)
                    if new_value is not None:
                        workspace.attributes[k] = new_value
                elif rule(node, workspace, k, v) is False:  # pragma: no cover
                    break

        return workspace

    ###################
    # js_embed method #
    ###################

    def js_embed(self, d: dict):
        return Breakable(
            start="{",
            body=join(
                [
                    Sequence(self.js_embed(k), ": ", self.js_embed(v))
                    for k, v in d.items()
                ],
                sep=", ",
            ),
            end="}",
        )

    def js_embed(self, seq: Union[list, tuple]):
        return Breakable(
            start="[",
            body=join(map(self.js_embed, seq), sep=", "),
            end="]",
        )

    def js_embed(self, x: Union[int, float, str, bool, type(None)]):
        return Text(json.dumps(x))

    def js_embed(self, expr: resource.JSExpression):
        return expr.code

    def js_embed(self, t: Tag):
        innerhtml = str(t)
        return f"$$HREPR.fromHTML({self.js_embed(innerhtml)})"

    def js_embed(self, j: J):
        resources = []
        jd = j._data

        if not j._path or not isinstance(j._path[0], str):
            raise Exception(
                "The J constructor should first be invoked with a string."
            )

        symbol, *path = j._path

        if jd.stylesheet is not None:
            styles = (
                jd.stylesheet
                if isinstance(jd.stylesheet, Sequence)
                else [jd.stylesheet]
            )
            resources.extend(
                [
                    src
                    if isinstance(src, Tag)
                    else H.link(rel="stylesheet", href=src)
                    for src in styles
                ]
            )
        if jd.namespace is not None:
            varname = gensym(symbol)
            resources.append(
                Module(
                    module=jd.namespace,
                    symbol=None if symbol == "default" else symbol,
                    varname=varname,
                )
            )
        elif jd.src is not None:
            varname = symbol
            resources.append(Script(src=jd.src))
        elif jd.code is not None:
            varname = symbol
            resources.append(Code(code=jd.code))
        else:
            varname = symbol

        assert varname is not None

        result = varname
        prev_result = varname
        last_symbol = None

        for entry in path:
            if isinstance(entry, str):
                prev_result = result
                last_symbol = entry
                result = Sequence(result, ".", entry)
            elif isinstance(entry, (list, tuple)):
                result = Breakable(
                    start="$$HREPR.ucall(",
                    body=join(
                        [
                            prev_result,
                            self.js_embed(last_symbol),
                            *[self.js_embed(x) for x in entry],
                        ],
                        sep=",",
                    ),
                    end=")",
                )
            else:  # pragma: no cover
                raise TypeError()

        if resources:
            result = Sequence(result, resources=resources)
        return result

    def js_embed(self, i: Into):
        return Text("$$INTO", resources=[i])

    def js_embed(self, res: resource.Resource):
        return self.js_embed(res.obj)

    def js_embed(self, x: object):
        if hasattr(x, "__js_embed__"):
            return x.__js_embed__(self)
        else:
            raise TypeError(
                f"Resources of type {type(x).__name__} cannot be serialized to JavaScript."
            )

    #####################
    # attr_embed method #
    #####################

    def attr_embed(self, value: bool):
        if value is False:
            return None
        elif value is True:
            return value

    def attr_embed(self, value: str):
        return self.expand_resources(value, self.attr_embed)

    def attr_embed(self, value: Union[int, float]):
        return str(value)

    def attr_embed(self, elements: Union[list, tuple, set, frozenset]):
        return " ".join(self.attr_embed(elem) for elem in elements)

    def attr_embed(self, style: dict):
        return "".join(f"{k}:{v};" for k, v in style.items())

    def attr_embed(self, expr: resource.JSExpression):
        return self.expand_resources(expr.code, self.js_embed)

    def attr_embed(self, t: Tag):
        tag_id = t.get_attribute("id", None)
        if not tag_id:
            raise ValueError(f"Cannot embed <{t.name}> element without an id.")
        return f"#{tag_id}"

    def attr_embed(self, x: object):
        if hasattr(x, "__attr_embed__"):
            return x.__attr_embed__(self)
        else:
            raise TypeError(
                f"Resources of type {type(x).__name__} cannot be serialized as an attribute."
            )

    #############
    # Interface #
    #############

    def generate(self, node, filter_resources=True):
        ws = self.node_embed(node)
        body = self._text_parts(ws)

        extra = Breakable(
            start=None,
            body=[self._text_parts(self.node_embed(x)) for x in ws.extra],
            end=None,
        )

        if filter_resources is True:
            filter_resources = ResourceDeduplicator()
        elif filter_resources is None:  # pragma: no cover
            filter_resources = no_resources

        resources = []
        for r in ws.resources:
            if not filter_resources(r):
                continue
            entry, more_extra, more_resources = self.generate(r)
            assert more_extra.empty()
            assert more_resources.empty()
            resources.append(entry)

        resources = Breakable(start=None, body=resources, end=None)

        return body, extra, resources

    def __call__(self, node):
        body, extra, _ = self.generate(node)
        return f"{body}{extra}"


standard_html = HTMLGenerator()
