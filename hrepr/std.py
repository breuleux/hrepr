def standard(hrepr, obj, *, cls=None, tag="span"):
    """
    Standard representation for objects, used when there is no
    handler for its type in type_handlers on the HRepr object,
    and no __hrepr__ method on obj. For an object of class 'klass',
    the result is:

    ``<span class="hrepr-klass">{escape(str(obj))}</span>``

    Where ``{escape(str(obj))}`` is the HTML-escaped string representation
    of the object.

    Args:
        obj: The object to represent.
        cls (optional): The class name for the representation. If None,
            stdrepr will use ``'hrepr-' + obj.__class__.___name__``
        tag (optional): The tag for the representation, defaults to
            'span'.
    """
    if cls is None:
        cls = f"hrepr-{obj.__class__.__name__}"
    return getattr(hrepr.H, tag)[cls](str(obj))


# def short(hrepr, obj, *, cls=None, tag="span"):
#     """
#     Standard short representation for objects, used for objects at
#     a depth that exceeds ``hrepr_object.config.max_depth``. That
#     representation is just the object's type between ``<>``s, e.g.
#     ``<MyClass>``.

#     This behavior can be overriden with a ``__hrepr_short__`` method
#     on the object, or an entry in ``hrepr_object.type_handlers_short``.

#     Args:
#         obj: The object to represent.
#         cls (optional): The class name for the representation. If None,
#             stdrepr will use ``'hrepr-' + obj.__class__.___name__``
#         tag (optional): The tag for the representation, defaults to
#             'span'.
#     """
#     cls_name = obj.__class__.__name__
#     if cls is None:
#         cls = f"hrepr-short-{cls_name}"
#     return getattr(hrepr.H, tag)[cls](f"<{cls_name}>")


def iterable(hrepr, obj, *, cls=None, before=None, after=None):
    """
    Helper function to represent iterables. StdHRepr calls this on
    lists, tuples, sets and frozensets, but NOT on iterables in general.
    This method may be called to produce custom representations.

    Arguments:
        obj (iterable): The iterable to represent.
        cls (optional): The class name for the representation. If None,
            stdrepr will use ``'hrepr-' + obj.__class__.___name__``
        before (optional): A string or a Tag to prepend to the elements.
        after (optional): A string or a Tag to append to the elements.
    """
    if cls is None:
        cls = f"hreprt-{obj.__class__.__name__}"
    children = [hrepr(a) for a in obj]
    return titled_box(hrepr, (before, after), children, "h", "h")[cls]


def instance(
    self,
    title,
    elements,
    *,
    cls=None,
    short=False,
    quote_string_keys=False,
    delimiter=None,
):
    """
    Helper function to represent objects.

    Arguments:
        title: A title string displayed above the box containing
            the elements, or a pair of two strings that will be
            displayed left and right (e.g. a pair of brackets).
        elements: A dict or list of (key, value) pairs, which will be
            displayed in a table in the order given.
        cls: A class to give to the result.
        short: Whether to use short or long form. Short form
            displays the elements as ``k=v``, appended horizontally.
            The alternative is a table, with associations stacked
            vertically.
        quote_string_keys: If True, string keys will be displayed
            with quotes around them. Default is False.
        delimiter: The character to use to separate key and
            value. By default '↦' if quote_string_keys is True.
    """
    if isinstance(elements, dict):
        elements = list(elements.items())

    H = self.H

    if delimiter is None and quote_string_keys is True:
        delimiter = " ↦ "

    def wrap(x):
        if not quote_string_keys and isinstance(x, str):
            return x
        else:
            return self(x)

    if short:
        contents = []
        for k, v in elements:
            kv = H.div["hrepr-instance-kvpair"](
                wrap(k), delimiter or "", self(v)
            )
            contents.append(kv)
    else:
        t = H.table()["hrepr-instance-table"]
        for k, v in elements:
            tr = H.tr(H.td(wrap(k)))
            if delimiter is not None:
                tr = tr(H.td["hrepr-delimiter"](delimiter))
            tr = tr(H.td(self(v)))
            t = t(tr)
        contents = [t]

    title_brackets = isinstance(title, tuple) and len(title) == 2
    horizontal = short or title_brackets

    rval = titled_box(
        self,
        title,
        contents,
        "h" if title_brackets else "v",
        "h" if short else "v",
    )

    if cls:
        rval = rval[cls]

    return rval


def titled_box(self, titles, contents, tdir="h", cdir="h"):
    """
    Helper function to build a box containing a list of elements,
    with a title above and/or below, or left and/or right of the
    box. (e.g. a class name on top, or brackets on both sides.)

    The elements given must already have been transformed into
    Tag instances.

    Arguments:
        titles: A pair of strings to display on top and bottom
            (if tdir=='v') or left and right (if tdir=='h').
            If either or both titles are None, they will be
            omitted.
        contents: A list of Tags.
        tdir: tdir=='h' (default) means the titles will be on
            the left and right. tdir=='v' means they will be
            on top and bottom.
        cdir: cdir=='h' (default) means the contents will be
            stacked horizontally. cdir=='v' means they will
            be stacked vertically.
    """
    H = self.H

    def wrapt(x):
        return H.div["hrepr-title"](x)

    rval = H.div[f"hrepr-titled-{tdir}"]
    contents = H.div[f"hrepr-contents-{cdir}"].fill(contents)

    if isinstance(titles, tuple) and len(titles) == 2:
        open, close = titles
    else:
        open, close = titles, None

    if open:
        rval = rval(wrapt(open))
    rval = rval(contents)
    if close:
        rval = rval(wrapt(close))

    return rval
