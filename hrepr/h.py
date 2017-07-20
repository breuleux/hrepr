
import os.path
from html import escape


# CSS for hrepr
styledir = f'{os.path.dirname(__file__)}/style'
css_nbreset = open(f'{styledir}/nbreset.css').read()
css_hrepr = open(f'{styledir}/hrepr.css').read()


# These tags are self-closing and cannot have children.
_void_tags = {'area', 'base', 'br', 'col', 'command', 'embed',
              'hr', 'img', 'input', 'keygen', 'link', 'meta',
              'param', 'source', 'track', 'wbr'}


# We do not escape string children for these tags.
_raw_tags = {'raw', 'script', 'style'}


# These tags do not correspond to real HTML tags. They cannot have
# attributes, and their children are simply concatenated and inlined
# in the parent.
_virtual_tags = {None, 'inline', 'raw'}


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
        resources (set): Set of resources needed by this node or its
            children.
    """

    def __init__(self, name, attributes=None, children=None):
        self.name = name
        self.attributes = attributes or {}
        self.children = children or ()
        self.resources = set()

    def __getitem__(self, items):
        if not isinstance(items, tuple):
            items = (items,)
        classes = self.attributes.get('class', frozenset()) | frozenset(items)
        return Tag(self.name,
                   {**self.attributes, 'class': classes},
                   self.children)

    def __call__(self, *children, **attributes):
        if len(children) > 0 and isinstance(children[0], dict):
            attributes = {**children[0], **attributes}
            children = children[1:]
        return Tag(self.name,
                   {**self.attributes, **attributes},
                   self.children + children)

    def __eq__(self, other):
        return isinstance(other, Tag) \
            and self.name == other.name \
            and self.attributes == other.attributes \
            and self.children == other.children

    def __hash__(self):
        return hash(self.name) \
            ^ hash(tuple(self.attributes.items())) \
            ^ hash(self.children)

    def __repr__(self):
        return str(self)

    def __str__(self):
        escape_children = \
            not self.attributes.get('__raw', self.name in _raw_tags)

        def convert_attribute(k, v):
            if v is True:
                return k
            elif v is False:
                return ''
            elif isinstance(v, (set, frozenset)):
                res = ' '.join(escape(cls) for cls in v)
            else:
                res = escape(str(v))
            return f'{k}="{res}"'

        def convert_child(c):
            if isinstance(c, (list, tuple)):
                return ''.join(map(convert_child, c))
            elif isinstance(c, Tag):
                return str(c)
            elif escape_children:
                return escape(str(c))
            else:
                return str(c)

        attr = ' '.join(convert_attribute(k, v)
                        for k, v in self.attributes.items()
                        if not k.startswith('__'))
        if attr:
            # raw tag cannot have attributes, because it's not a real tag
            assert self.name not in _virtual_tags
            attr = ' ' + attr

        children = ''.join(map(convert_child, self.children))
        if self.name in _virtual_tags:
            # Virtual tags just inlines their contents directly.
            return children
        if self.attributes.get('__void', self.name in _void_tags):
            assert len(self.children) == 0
            return f'<{self.name}{attr} />'
        else:
            return f'<{self.name}{attr}>{children}</{self.name}>'

    def _repr_html_(self):
        """
        Jupyter Notebook hook to print this element as HTML.
        """
        nbreset = f'<style>{css_nbreset}</style>'
        resources = ''.join(map(str, self.resources))
        return f'{nbreset}{resources}<div class="hrepr">{self}</div>'

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
        utf8 = H.meta({'http-equiv': 'Content-type'},
                      content="text/html",
                      charset="UTF-8")
        return H.inline(H.raw('<!DOCTYPE html>'),
                        H.html(H.head(utf8, *self.resources),
                               H.body(self)))



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
    def __getattr__(self, tag_name):
        return Tag(tag_name)

