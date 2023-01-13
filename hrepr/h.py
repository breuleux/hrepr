import os.path
from itertools import count
from types import GeneratorType
from typing import Union

from ovld import ovld

from .textgen import Context

# CSS for hrepr
styledir = f"{os.path.dirname(__file__)}/style"
css_nbreset = open(f"{styledir}/nbreset.css", encoding="utf-8").read()

# Used by __str__, set by __init__ to avoid a circular dependency
standard_html = None

current_autoid = count()


def _nextid():
    return f"AID_{next(current_autoid)}"


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

    def get_attribute(self, attr, dflt):
        return self.attributes.get(attr, dflt)

    def parts_and_resources(self):
        return standard_html.generate(self)

    def text_parts(self):
        return self.parts_and_resources()[0]

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

    def autoid(self):
        return self(id=_nextid())

    def __getitem__(self, items):
        if not isinstance(items, tuple):
            items = (items,)
        assert all(isinstance(item, str) for item in items)
        attributes = {}
        classes = [it for it in items if not it.startswith("#")]
        if classes:
            attributes["class"] = [*self.attributes.get("class", ()), *classes]
        ids = [it for it in items if it.startswith("#")]
        if ids:
            the_id = ids[-1][1:]
            if the_id == "":
                the_id = f"AID_{next(current_autoid)}"
            attributes["id"] = the_id
        return self.fill(attributes=attributes)

    def __call__(self, *children, **attributes):
        if "__constructor" in attributes:
            if "id" not in attributes and "id" not in self.attributes:
                attributes["id"] = _nextid()
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
        body, extra, resources = self.parts_and_resources()
        elem = H.div(
            H.style(css_nbreset), resources, H.div["hrepr"](body, extra)
        )
        return str(elem)

    def as_page(self, pretty=False, **format_options):
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
        body, extra, resources = self.parts_and_resources()
        H = HTML()
        utf8 = H.meta(
            {"http-equiv": "Content-type"}, content="text/html", charset="UTF-8"
        )
        node = H.inline(
            H.raw("<!DOCTYPE html>"),
            H.html(H.head(utf8, resources), H.body(body, extra)),
        )
        if not pretty:
            format_options["max_col"] = None
        return node.pretty(**format_options)


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
