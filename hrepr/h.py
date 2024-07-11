from itertools import count
from types import GeneratorType

# Used by __str__, set by __init__ to avoid a circular dependency
standard_html = None

current_id = count()


def gensym(symbol):
    return f"{symbol}__{next(current_id)}"


def flatten(seq):
    results = []
    for element in seq:
        if isinstance(element, (list, tuple, GeneratorType)):
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

    __slots__ = (
        "_constructed",
        "_parent",
        "_name",
        "_attributes",
        "_children",
        "_resources",
        "_require_id",
        "_serial",
    )

    specialized_tags = {}

    @classmethod
    def specialize(cls, name):
        """Return a new subclass specialized for the given tag name."""
        assert cls is Tag
        if name not in cls.specialized_tags:
            cls.specialized_tags[name] = type(
                f"Tag::{name}", (Tag,), {"__slots__": ()}
            )
        return cls.specialized_tags[name]

    def __init__(
        self,
        name=None,
        parent=None,
        attributes=None,
        children=None,
        resources=None,
    ):
        self._constructed = False
        self._parent = parent
        self._name = name
        self._attributes = attributes
        self._children = children
        self._resources = resources
        self._require_id = False
        self._serial = next(current_id)

    def _do_cache(self):
        self._constructed = True

        sequence = [self]
        current = self
        while current._parent is not None:
            sequence.append(current._parent)
            current = current._parent
        self._name = current._name

        attributes = {}
        children = []
        resources = []
        serial = None

        for part in reversed(sequence):
            if part._require_id:
                serial = part._serial
            if part._attributes:
                attributes.update(part._attributes)
            if part._children:
                children.extend(part._children)
            if part._resources:
                resources.extend(part._resources)

        if serial is not None and "id" not in attributes:
            attributes["id"] = f"H{serial}"

        self._parent = None
        self._attributes = attributes
        self._children = tuple(flatten(children))
        self._resources = tuple(resources)

    @property
    def name(self):
        if not self._constructed:
            self._do_cache()
        return self._name

    @property
    def attributes(self):
        if not self._constructed:
            self._do_cache()
        return self._attributes

    @property
    def children(self):
        if not self._constructed:
            self._do_cache()
        return self._children

    @property
    def resources(self):
        if not self._constructed:  # pragma: no cover
            self._do_cache()
        return self._resources

    def fill(self, children=None, attributes=None, resources=None):
        if isinstance(resources, Tag):
            resources = (resources,)
        return type(self)(
            parent=self,
            attributes=attributes,
            children=children,
            resources=resources,
        )

    def get_attribute(self, attr, dflt):
        return self.attributes.get(attr, dflt)

    def ensure_id(self):
        if self._require_id or (
            self._attributes and self._attributes.get("id", None)
        ):
            return self
        elif self._constructed:
            raise Exception(
                "It is too late to ensure that this node has an ID, because"
                " its attributes or children have already been accessed."
                " Either construct with an explicit id, or call ensure_id() earlier."
            )
        else:
            self._require_id = True
            return self

    @property
    def id(self):
        self.ensure_id()
        return self.attributes["id"]

    def __getitem__(self, items):
        if not isinstance(items, tuple):
            items = (items,)
        assert all(isinstance(item, str) for item in items)
        attributes = {}
        classes = [it for it in items if not it.startswith("#")]
        if classes:
            attributes["class"] = (*self.attributes.get("class", ()), *classes)
        return self.fill(attributes=attributes)

    def __call__(self, *children, resources=None, id=None, **attributes):
        attributes = {
            attr.replace("_", "-"): value for attr, value in attributes.items()
        }
        if len(children) > 0 and isinstance(children[0], dict):
            attributes = {**children[0], **attributes}
            children = children[1:]
        if id and id is not True:
            attributes["id"] = id
        result = self.fill(
            children=children, attributes=attributes, resources=resources
        )
        if id is True:
            result = result.ensure_id()
        return result

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
        return standard_html.to_string(self)

    def _repr_html_(self):  # pragma: no cover
        """
        Jupyter Notebook hook to print this element as HTML.
        """
        return standard_html.to_jupyter(self)

    def as_page(self):
        """
        Wrap this Tag as a self-contained webpage.
        """
        return standard_html.as_page(self)


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
        self._tag_class = tag_class
        self._instantiate = instantiate

    def __getattr__(self, tag_name):
        tag_name = tag_name.replace("_", "-")
        tag_class = self._tag_class
        if hasattr(tag_class, "specialize"):
            tag_class = tag_class.specialize(tag_name)
        if self._instantiate:
            rval = tag_class(name=tag_name)
        else:
            rval = tag_class  # pragma: no cover
        setattr(self, tag_name, rval)
        return rval


H = HTML(tag_class=Tag, instantiate=True)
HType = HTML(tag_class=Tag, instantiate=False)
