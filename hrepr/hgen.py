from html import escape
from itertools import count
from types import SimpleNamespace

from ovld import OvldMC, ovld

from .h import H, Tag, iterate_children
from .hjson import dump as jdump
from .textgen import Breakable, Text


class HTMLGenerator(metaclass=OvldMC):
    def __init__(self, rules, dump):
        self.rules = rules
        self._jdump = dump

    def json(self, obj, **fmt):
        return self._jdump(obj).to_string(**fmt)

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
        if value is False:
            return
        elif value is True:
            workspace.attributes[attr] = value
        elif isinstance(value, (list, tuple, set, frozenset)):
            workspace.attributes[attr] = " ".join(escape(cls) for cls in value)
        elif isinstance(value, str):
            workspace.attributes[attr] = escape(value)
        else:
            # workspace.attributes[attr] = escape(json.dumps(value))
            workspace.attributes[attr] = escape(self.json(value))

    @ovld
    def process(self, node: str):
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
            resources=[],
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

        tag_rule = self.rules.get(f"tag:{node.name}", self._default_tag)
        if tag_rule(self, node, workspace, self.default_tag) is False:
            pass
        else:
            for k, v in node.attributes.items():
                rule = self.rules.get(f"attr:{k}", self._default_attr)
                if (
                    rule(self, node, workspace, k, v, self.default_attr)
                    is False
                ):
                    break

        return workspace

    def _text_parts(self, workspace):
        def convert_child(c):
            if isinstance(c, str):
                if workspace.escape_children:
                    return escape(str(c))
                else:
                    return c
            else:
                return self._text_parts(c)

        attr = "".join(
            f" {k}" if v is True else f' {k}="{v}"'
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

    def generate(self, node):
        ws = self.process(node)
        to_process = [ws, *[self.process(x) for x in ws.extra]]
        parts = [self._text_parts(x) for x in to_process]
        if len(parts) == 1:
            return parts[0]
        else:
            return Breakable(start=None, body=parts, end=None)


##########################
# Special JSON generator #
##########################


# _type = type


# @ovld
# def jdump(self, d: dict):
#     return Breakable(
#         start="{",
#         body=join(
#             [Sequence(self(k), ": ", self(v)) for k, v in d.items()], sep=", "
#         ),
#         end="}",
#     )


# @ovld
# def jdump(self, seq: Union[list, tuple]):
#     return Breakable(start="[", body=join(map(self, seq), sep=", "), end="]",)


# @ovld
# def jdump(self, x: Union[int, float, str, bool, _type(None)]):
#     return Text(json.dumps(x))


# @ovld
# def jdump(self, fn: Union[FunctionType, MethodType]):
#     return self(None)


# @ovld
# def jdump(self, t: HType.self):
#     return f"self"


# @ovld
# def jdump(self, t: Tag):
#     tag_id = t.get_attribute("id")
#     if not tag_id:
#         raise ValueError(f"Cannot embed <{t.name}> element without an id.")
#     return f"document.getElementById('{tag_id}')"


# @ovld
# def jdump(self, d: object):
#     raise TypeError(
#         f"Objects of type {type(d).__name__} cannot be serialized to JavaScript."
#     )


# def dumps(obj, **fmt):
#     return jdump(obj).to_string(**fmt)


standard_html = HTMLGenerator({}, jdump)


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
_raw_tags = {"script", "style"}

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


constructor_template_script = """{imp}
const self = document.getElementById('{node_id}');
const arglist = {arguments};
const obj = new {symbol}(...arglist);
window.${node_id} = obj;
"""


id_counter = count()


@standard_html.register("attr:constructor")
def constructor_attribute(self, node, workspace, key, value, default):
    if "id" in node.attributes:
        node_id = node.attributes["id"]
    else:
        node_id = workspace.attributes["id"] = f"$hrepr${next(id_counter)}"

    module = value.get("module", None)

    if module:
        symbol = value.get("symbol", None)
        if symbol is None:
            symbol = "constructor"
            imp = f"import constructor from '{module}';"
        else:
            imp = f"import {{{symbol}}} from '{module}';"
    else:
        symbol = value["symbol"]
        imp = ""

    if "options" in value:
        assert "arguments" not in value
        arguments = [H.self(), value["options"]]
    elif "arguments" in value:
        arguments = value["arguments"]
        if isinstance(arguments, dict):
            arguments = [arguments]
    else:
        arguments = [H.self()]

    sc = H.script(
        constructor_template_script.format(
            imp=imp,
            symbol=symbol,
            node_id=node_id,
            arguments=self.json(arguments, tabsize=4, max_col=80),
        ),
        type="module",
    )

    workspace.extra.append(sc)


# @standard_html.register("attr:--resources")
# def constructor_resources(node, workspace, key, value, default):
#     if not isinstance(value, Sequence):
#         workspace.resources.append(value)
#     else:
#         workspace.resources.extend(value)
