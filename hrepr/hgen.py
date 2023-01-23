import re
from html import escape
from types import SimpleNamespace
from typing import Sequence, Union

from ovld import OvldMC, ovld

from . import h as hmodule
from . import resource
from .embed import attr_embed, js_embed
from .h import H, Tag, iterate_children
from .textgen import Breakable, Text, TextFormatter


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
            return self.expand_resources(embed(res.obj), embed)

        return re.sub(
            pattern=rf"\[{resource.embed_key}:([0-9]+)\]",
            string=value,
            repl=sub,
        )

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
            assert not more_extra
            assert not more_resources
            resources.append(entry)

        resources = Breakable(start=None, body=resources, end=None)

        return body, extra, resources

    def __call__(self, node):
        body, extra, _ = self.generate(node)
        return f"{body}{extra}"


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


constructor_lib = H.script(
    """
$$HREPR = {
    prepare(node_id) {
        const self = document.getElementById(node_id);
        let resolve = null;
        self.__object = new Promise((rs, rj) => { resolve = rs });
        self.__object.__resolve = resolve;
    },
    isFunc(x) {
        let hasprop = prop => Object.getOwnPropertyNames(x).includes(prop);
        return (hasprop("arguments") || !hasprop("prototype"));
    }
}
"""
)


constructor_promise_script = "$$HREPR.prepare('{node_id}')"


constructor_template_script = """{imp}
const self = document.getElementById('{node_id}');
const arglist = {arguments};
let obj = $$HREPR.isFunc({symbol}) ? {symbol}(...arglist) : new {symbol}(...arglist);
self.__object.__resolve(obj);
"""


@standard_html.register("attr:--constructor")
def constructor_attribute(self, node, workspace, key, value, default):
    if "id" in node.attributes:
        node_id = node.attributes["id"]
    else:  # pragma: no cover
        # Setting __constructor should normally set an id, so this may not trigger
        autoid = f"$hrepr${next(hmodule.current_autoid)}"
        node_id = workspace.attributes["id"] = autoid

    module = value.get("module", None)
    script = value.get("script", None)

    workspace.resources.append(constructor_lib)
    if module:
        assert not isinstance(module, (list, tuple))
        assert script is None
        symbol = value.get("symbol", None)
        module = self.js_embed(module)
        if symbol is None:
            symbol = "constructor"
            imp = f"import constructor from {module};"
        elif symbol.startswith("default."):
            imp = f"import dflt from {module};"
            symbol = symbol.replace("default.", "dflt.")
        else:
            rootsym, sep, props = symbol.partition(".")
            imp = f"import {{{rootsym}}} from {module};"
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

    if "stylesheet" in value:
        sheet = value["stylesheet"]
        sheet = [
            src if isinstance(src, Tag) else H.link(rel="stylesheet", href=src)
            for src in (sheet if isinstance(sheet, (list, tuple)) else [sheet])
        ]
        workspace.resources.extend(sheet)

    sc_promise = H.script(constructor_promise_script.format(node_id=node_id))
    workspace.extra.append(sc_promise)

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


@standard_html.register("attr:style")
def attr_style(self, node, workspace, key, value, default):
    if isinstance(value, dict):
        value = "".join(f"{k}:{v};" for k, v in value.items())
    workspace.attributes["style"] = value
