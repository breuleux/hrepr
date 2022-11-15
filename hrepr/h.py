import json
import os.path
from html import escape
from types import GeneratorType, SimpleNamespace
from typing import Union

from ovld import OvldMC, ovld

from .textgen import Breakable, Context, Text

# CSS for hrepr
styledir = f"{os.path.dirname(__file__)}/style"
css_nbreset = open(f"{styledir}/nbreset.css", encoding="utf-8").read()


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


# We do not escape string children for these tags.
_raw_tags = {"raw", "script", "style"}


# These tags do not correspond to real HTML tags. They cannot have
# attributes, and their children are simply concatenated and inlined
# in the parent.
_virtual_tags = {None, "inline", "raw"}


def flatten(seq):
    results = []
    for element in seq:
        if isinstance(element, (list, tuple)):
            results.extend(flatten(element))
        else:
            results.append(element)
    return results


class Tag:
    """
    Representation of an HTML tag.

    .. note::

        Create tags using an instance of the HTML class.

    A Tag should be immutable, but you can create modified versions
    of a tag by calling it with additional attributes or children,
    or indexing it with class names:

    >>> H = HTML()
    >>> tag = H.div()
    >>> tag
    <div></div>
    >>> tag(1, 2, 3)
    <div>123</div>
    >>> tag['klass']
    <div class="klass"></div>
    >>> tag(id='dividi')
    <div id="dividi"></div>
    >>> tag['klass'](id='dividi')(1, 2, 3)
    <div class="klass" id="dividi">123</div>

    Underscores in attributes are converted to dashes when they are
    given as keyword arguments. Attribute names with underscores can
    be provided via the ``fill`` method.

    Attributes:
        name (str): The tag name (div, span, a, etc.)
        attributes (dict): A dictionary of attributes. Attributes that
            start with ``__`` or ``--`` are reserved for internal use.
        children (tuple): Children of this node.
        resources (tuple): List of resources needed by this node or its
            children.
    """

    specialized_tags = {}

    @classmethod
    def specialize(cls, name):
        """Return a new subclass specialized for the given tag name."""
        assert cls is Tag
        if name not in cls.specialized_tags:
            cls.specialized_tags[name] = type(f"Tag::{name}", (Tag,), {})
        return cls.specialized_tags[name]

    def __init__(self, name, attributes=None, children=None, resources=None):
        self.name = name
        self.attributes = attributes or {}
        self.children = tuple(flatten(children or ()))
        self.resources = () if resources is None else tuple(resources)

    def fill(self, children=None, attributes=None, resources=None):
        if not children and not attributes and not resources:
            return self
        children = (*self.children, *children) if children else self.children
        attributes = (
            {**self.attributes, **attributes} if attributes else self.attributes
        )
        if isinstance(resources, Tag):
            resources = (resources,)
        resources = (
            tuple([*self.resources, *resources])
            if resources
            else self.resources
        )
        return type(self)(
            name=self.name,
            attributes=attributes,
            children=children,
            resources=resources,
        )

    def collect_resources(self, coll=None, exclude=None):
        coll = [] if coll is None else coll
        exclude = set() if exclude is None else exclude
        for res in self.resources:
            if res not in exclude:
                res.collect_resources(coll=coll, exclude=exclude)
                coll.append(res)
        exclude.update(self.resources)
        for child in iterate_children(self.children):
            if isinstance(child, Tag):
                child.collect_resources(coll=coll, exclude=exclude)
        return coll

    def get_attribute(self, attr, dflt):
        return self.attributes.get(attr, dflt)

    def text_parts(self):
        return standard_html.generate(self)

    def pretty(self, **config):
        rval, _ = self.text_parts().format(
            Context(
                tabsize=4,
                max_col=80,
                offset=0,
                line_offset=0,
                overflow="allow",
            ).replace(**config)
        )
        return rval

    def __getitem__(self, items):
        if not isinstance(items, tuple):
            items = (items,)
        assert all(isinstance(item, str) for item in items)
        classes = self.attributes.get("class", ()) + items
        return self.fill(attributes={"class": classes})

    def __call__(self, *children, **attributes):
        attributes = {
            attr.replace("_", "-"): value for attr, value in attributes.items()
        }
        if len(children) > 0 and isinstance(children[0], dict):
            attributes = {**children[0], **attributes}
            children = children[1:]
        return self.fill(children, attributes)

    def __eq__(self, other):
        return (
            isinstance(other, Tag)
            and self.name == other.name
            and self.attributes == other.attributes
            and self.children == other.children
            and self.resources == other.resources
        )

    def __hash__(self):
        return hash(
            (
                self.name,
                tuple(self.attributes.items()),
                self.children,
                self.resources,
            )
        )

    def __repr__(self):
        return str(self)

    def __str__(self):
        return self.pretty(max_col=None)

    def _repr_html_(self):  # pragma: no cover
        """
        Jupyter Notebook hook to print this element as HTML.
        """
        elem = H.div(
            H.style(css_nbreset),
            *self.collect_resources(),
            H.div["hrepr"](self),
        )
        return str(elem)

    def as_page(self):
        """
        Wrap this Tag as a self-contained webpage. Create a page with
        the following structure:

        .. code-block:: html

            <!DOCTYPE html>
            <html>
              <head>
                <meta http-equiv="Content-type"
                      content="text/html"
                      charset="UTF-8" />
                {self.resources}
              </head>
              <body>
                {self}
              </body>
            </html>
        """
        H = HTML()
        utf8 = H.meta(
            {"http-equiv": "Content-type"}, content="text/html", charset="UTF-8"
        )
        return H.inline(
            H.raw("<!DOCTYPE html>"),
            H.html(H.head(utf8, *self.collect_resources()), H.body(self)),
        )


@ovld
def iterate_children(self, children: Union[list, tuple, GeneratorType]):
    for child in children:
        yield from self(child)


@ovld
def iterate_children(self, child: object):
    yield child


class HTML:
    """
    Tag factory:

    >>> H = HTML()
    >>> H.div()
    <div></div>
    >>> H.a(href="http://cool.cool.cool")("My cool site")
    <a href="http://cool.cool.cool">My cool site</a>
    >>> H.span["cool", "beans"]("How stylish!")
    <span class="cool beans">How stylish!</span>
    """

    def __init__(self, tag_class=Tag, instantiate=True):
        self.tag_class = tag_class
        self.instantiate = instantiate

    def __getattr__(self, tag_name):
        tag_name = tag_name.replace("_", "-")
        tag_class = self.tag_class
        if hasattr(tag_class, "specialize"):
            tag_class = tag_class.specialize(tag_name)
        if self.instantiate:
            return tag_class(tag_name)
        else:
            return tag_class


H = HTML(tag_class=Tag, instantiate=True)
HType = HTML(tag_class=Tag, instantiate=False)


class HTMLGenerator(metaclass=OvldMC):
    def __init__(self, rules):
        self.rules = rules

    def register(self, rule, fn=None):
        def reg(fn):
            self.rules[rule] = fn
            return fn

        if fn is None:
            return reg
        else:
            return reg(fn)

    def _default_tag(self, node, workspace, default):
        return default(node, workspace)

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
        elif isinstance(value, (tuple, set, frozenset)):
            workspace.attributes[attr] = " ".join(escape(cls) for cls in value)
        elif isinstance(value, str):
            workspace.attributes[attr] = escape(value)
        else:
            workspace.attributes[attr] = escape(json.dumps(value))

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
        if tag_rule(node, workspace, self.default_tag) is False:
            pass
        else:
            for k, v in node.attributes.items():
                rule = self.rules.get(f"attr:{k}", self._default_attr)
                if rule(node, workspace, k, v, self.default_attr) is False:
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
        to_process = [ws, *ws.extra]
        parts = [self._text_parts(x) for x in to_process]
        if len(parts) == 1:
            return parts[0]
        else:
            return Breakable(start=None, body=parts, end=None)


standard_html = HTMLGenerator({})


######################################
# Handlers for void/raw/special tags #
######################################


def raw_tag(node, workspace, default):
    workspace.escape_children = False
    return default(node, workspace)


def void_tag(node, workspace, default):
    assert not workspace.children
    workspace.open = node.name
    workspace.close = None


def virtual_tag(node, workspace, default):
    return


def raw_virtual_tag(node, workspace, default):
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
