import os.path
from html import escape
from types import GeneratorType

from ovld import ovld

from .textgen import Breakable, Context, Text

# CSS for hrepr
styledir = f"{os.path.dirname(__file__)}/style"
css_nbreset = open(f"{styledir}/nbreset.css", encoding="utf-8").read()
css_hrepr = open(f"{styledir}/hrepr.css", encoding="utf-8").read()


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

    Attributes:
        name (str): The tag name (div, span, a, etc.)
        attributes (dict): A dictionary of attributes. Attributes that
            start with ``__`` are reserved for internal use.
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
        self.children = children or ()
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

    def is_virtual(self):
        return self.name in _virtual_tags

    def text_parts(self):
        is_virtual = self.is_virtual()
        escape_children = not self.attributes.get(
            "__raw", self.name in _raw_tags
        )

        def convert_attribute(k, v):
            if v is True:
                return k
            elif v is False:
                return ""
            elif isinstance(v, (tuple, frozenset)):
                res = " ".join(escape(cls) for cls in v)
            else:
                res = escape(str(v))
            return f'{k}="{res}"'

        def convert_child(c):
            if isinstance(c, Tag):
                return c.text_parts()
            elif escape_children:
                return escape(str(c))
            else:
                return str(c)

        attr = " ".join(
            convert_attribute(k, v)
            for k, v in self.attributes.items()
            if not k.startswith("__")
        )
        if attr:
            # raw tag cannot have attributes, because it's not a real tag
            assert not is_virtual
            attr = " " + attr

        children = list(map(convert_child, iterate_children(self.children)))
        if is_virtual:
            # Virtual tags just inlines their contents directly.
            return Breakable(start=None, body=children, end=None)
        if self.attributes.get("__void", self.name in _void_tags):
            assert len(self.children) == 0
            return Text(f"<{self.name}{attr} />")
        else:
            return Breakable(
                start=f"<{self.name}{attr}>",
                body=children,
                end=f"</{self.name}>",
            )

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
def iterate_children(self, children: (list, tuple, GeneratorType)):
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

    def __init__(self, tag_class=Tag):
        self.tag_class = tag_class

    def __getattr__(self, tag_name):
        tag_name = tag_name.replace("_", "-")
        tag_class = self.tag_class
        if hasattr(tag_class, "specialize"):
            tag_class = tag_class.specialize(tag_name)
        return tag_class(tag_name)


H = HTML(tag_class=Tag)
