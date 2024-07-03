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
    def __init__(self, tag_rules=None, attr_rules=None):
        self.tag_rules = tag_rules or {}
        self.attr_rules = attr_rules or {}

    def register(self, rule, fn=None):
        def reg(fn):
            if rule.startswith("tag:"):
                self.tag_rules[rule[4:]] = fn
            elif rule.startswith("attr:"):
                self.attr_rules[rule[5:]] = fn
            else:  # pragma: no cover
                raise ValueError(f"Unknown rule type: {rule}")
            return fn

        if fn is None:
            return reg
        else:
            return reg(fn)

    ############
    # Defaults #
    ############

    @staticmethod
    def _default_tag(self, node, workspace, default):
        return default(node, workspace)

    @staticmethod
    def _default_attr(self, node, workspace, attr, value, default):
        return default(node, workspace, attr, value)

    def default_tag(self, node, workspace):
        workspace.open = node.name
        workspace.close = node.name

    def default_attr(self, node, workspace, attr, value):
        new_value = self.attr_embed(value)
        if new_value is True:
            workspace.attributes[attr] = new_value
        elif isinstance(new_value, resource.JSExpression):
            workspace.attributes[attr] = self.expand_resources(
                new_value.code, self.js_embed
            )
        elif new_value is not None:
            workspace.attributes[attr] = self.expand_resources(
                new_value, self.attr_embed
            )

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

    ##################
    # process method #
    ##################

    def process(self, node: Union[str, TextFormatter]):
        return node

    def process(self, node: object):
        if hasattr(node, "__h__"):
            return self.process(node.__h__())
        else:
            return str(node)

    def process(self, node: J):
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

        workspace = self.process(element)
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

    def process(self, node: Tag):
        workspace = Workspace(
            open=None,
            close=None,
            attributes={},
            children=[],
            resources=list(node.resources),
            extra=[],
            escape_children=True,
        )

        workspace.children = [self.process(child) for child in node.children]
        for child in workspace.children:
            if getattr(child, "extra", None):
                workspace.extra += child.extra
                child.extra = []
            if getattr(child, "resources", None):
                workspace.resources += child.resources
                child.resources = []

        tag_rule = self.tag_rules.get(node.name, self._default_tag)
        if (
            tag_rule(self, node, workspace, self.default_tag) is False
        ):  # pragma: no cover
            pass
        else:
            for k, v in node.attributes.items():
                rule = self.attr_rules.get(k, self._default_attr)
                if (
                    rule(self, node, workspace, k, v, self.default_attr)
                    is False
                ):  # pragma: no cover
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

    def attr_embed(self, value: Union[str, int, float]):
        return str(value)

    def attr_embed(self, elements: Union[list, tuple, set, frozenset]):
        return " ".join(self.attr_embed(elem) for elem in elements)

    def attr_embed(self, expr: resource.JSExpression):
        return expr

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
        ws = self.process(node)
        body = self._text_parts(ws)

        extra = Breakable(
            start=None,
            body=[self._text_parts(self.process(x)) for x in ws.extra],
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


standard_html = HTMLGenerator(tag_rules={}, attr_rules={})


######################################
# Handlers for void/raw/special tags #
######################################


def raw_tag(self, node, workspace, default):
    workspace.escape_children = False
    return default(node, workspace)


def void_tag(self, node, workspace, default):
    assert not workspace.children
    workspace.open = node.name
    workspace.close = None


def virtual_tag(self, node, workspace, default):
    return


def raw_virtual_tag(self, node, workspace, default):
    workspace.escape_children = False


# These tags are self-closing and cannot have children.
_void_tags = {
    "area",
    "base",
    "br",
    "col",
    "command",
    "embed",
    "hr",
    "img",
    "input",
    "keygen",
    "link",
    "meta",
    "param",
    "source",
    "track",
    "wbr",
    "!DOCTYPE",
}

for t in _void_tags:
    standard_html.register(f"tag:{t}", void_tag)


# We do not escape string children for these tags.
_raw_tags = {"style"}

for t in _raw_tags:
    standard_html.register(f"tag:{t}", raw_tag)


# These tags do not correspond to real HTML tags. They cannot have
# attributes, and their children are simply concatenated and inlined
# in the parent.
_virtual_tags = {None, "inline"}

for t in _virtual_tags:
    standard_html.register(f"tag:{t}", virtual_tag)


_raw_virtual_tags = {"raw"}

for t in _raw_virtual_tags:
    standard_html.register(f"tag:{t}", raw_virtual_tag)


###################################
# Handlers for special attributes #
###################################


@standard_html.register("tag:script")
def script_tag(self, node, workspace, default):
    workspace.escape_children = False
    new_children = []
    for child in workspace.children:
        assert isinstance(child, str)
        new_children.append(self.expand_resources(child, self.js_embed))
    workspace.children = new_children
    return default(node, workspace)


@standard_html.register("attr:style")
def attr_style(self, node, workspace, key, value, default):
    if isinstance(value, dict):
        value = "".join(f"{k}:{v};" for k, v in value.items())
    workspace.attributes["style"] = value
