import re
from html import escape
from itertools import count
from types import SimpleNamespace
from typing import Sequence, Union

from ovld import OvldMC, ovld

from . import resource
from .embed import attr_embed, js_embed
from .h import H, Tag, iterate_children
from .textgen import Breakable, Text, TextFormatter


class HTMLGenerator(metaclass=OvldMC):
    def __init__(self, rules=None, *, attr_embed, js_embed):
        self.rules = rules or {}
        self.attr_embed = attr_embed
        self._js_embed = js_embed

    def fork(self, *, attr_embed=None, js_embed=None):
        return type(self)(
            dict(self.rules),
            attr_embed=attr_embed or self.attr_embed,
            js_embed=js_embed or self.js_embed,
        )

    def js_embed(self, obj, **fmt):
        x = self._js_embed(obj)
        if not isinstance(x, str):
            x = x.to_string(**fmt)
        return x

    def register(self, rule, fn=None):
        def reg(fn):
            self.rules[rule] = fn
            return fn

        if fn is None:
            return reg
        else:
            return reg(fn)

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
        new_value = self.attr_embed(attr, value)
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

    @ovld
    def process(self, node: Union[str, TextFormatter]):
        return node

    @ovld
    def process(self, node: object):
        return str(node)

    @ovld
    def process(self, node: Tag):
        workspace = SimpleNamespace(
            open=None,
            close=None,
            attributes={},
            children=[],
            resources=list(node.resources),
            extra=[],
            escape_children=True,
        )

        workspace.children = [
            self.process(child) for child in iterate_children(node.children)
        ]
        for child in workspace.children:
            if getattr(child, "extra", None):
                workspace.extra += child.extra
                child.extra = []
            if getattr(child, "resources", None):
                workspace.resources += child.resources
                child.resources = []

        tag_rule = self.rules.get(f"tag:{node.name}", self._default_tag)
        if (
            tag_rule(self, node, workspace, self.default_tag) is False
        ):  # pragma: no cover
            pass
        else:
            for k, v in node.attributes.items():
                rule = self.rules.get(f"attr:{k}", self._default_attr)
                if (
                    rule(self, node, workspace, k, v, self.default_attr)
                    is False
                ):  # pragma: no cover
                    break

        return workspace

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
            return embed(res.obj)

        return re.sub(
            pattern=rf"\[{resource.embed_key}:([0-9]+)\]",
            string=value,
            repl=sub,
        )

    def generate(self, node, process_resources=True):
        ws = self.process(node)
        to_process = [ws, *[self.process(x) for x in ws.extra]]
        parts = [self._text_parts(x) for x in to_process]
        if len(parts) == 1:
            tp = parts[0]
        else:
            tp = Breakable(start=None, body=parts, end=None)

        resources = {}
        for r in ws.resources if process_resources else []:
            if r in resources:
                continue
            entry, more_resources = self.generate(r)
            assert not more_resources
            resources[r] = entry
        resources = Breakable(
            start=None, body=list(resources.values()), end=None
        )

        return tp, resources

    def __call__(self, node):
        return str(self.generate(node)[0])


standard_html = HTMLGenerator(
    rules={}, attr_embed=attr_embed, js_embed=js_embed
)


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


constructor_template_script = """{imp}
const self = document.getElementById('{node_id}');
const arglist = {arguments};
let hasprop = prop => Object.getOwnPropertyNames({symbol}).includes(prop);
let obj = (hasprop("arguments") || !hasprop("prototype")) ? {symbol}(...arglist) : new {symbol}(...arglist);
window.${node_id} = obj;
"""


id_counter = count()


@standard_html.register("attr:--constructor")
def constructor_attribute(self, node, workspace, key, value, default):
    if "id" in node.attributes:
        node_id = node.attributes["id"]
    else:
        node_id = workspace.attributes["id"] = f"$hrepr${next(id_counter)}"

    module = value.get("module", None)
    script = value.get("script", None)

    if module:
        assert not isinstance(module, (list, tuple))
        assert script is None
        symbol = value.get("symbol", None)
        if symbol is None:
            symbol = "constructor"
            imp = f"import constructor from '{module}';"
        else:
            rootsym, sep, props = symbol.partition(".")
            imp = f"import {{{rootsym}}} from '{module}';"
    else:
        if script:
            script = [
                src
                if isinstance(src, Tag)
                else H.script(src=src, type="text/javascript")
                for src in (
                    script if isinstance(script, (list, tuple)) else [script]
                )
            ]
            workspace.resources.extend(script)
        symbol = value["symbol"]
        imp = ""

    if "options" in value:
        assert "arguments" not in value
        arguments = [H.self(), value["options"]]
    elif "arguments" in value:
        arguments = value["arguments"]
        if not isinstance(arguments, (list, tuple)):
            arguments = [arguments]
    else:
        arguments = [H.self()]

    sc = H.script(
        constructor_template_script.format(
            imp=imp,
            symbol=symbol,
            node_id=node_id,
            arguments=self.js_embed(arguments),
        ),
        type="module",
    )

    workspace.extra.append(sc)


@standard_html.register("attr:--resources")
def attr_resources(self, node, workspace, key, value, default):
    if not isinstance(value, Sequence):
        workspace.resources.append(value)
    else:
        workspace.resources.extend(value)
