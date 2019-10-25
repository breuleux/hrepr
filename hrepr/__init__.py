"""Extensible HTML representation for Python objects."""

from .h import Tag, HTML, css_hrepr
from copy import copy


class Config:
    def __init__(self, cfg):
        self.__dict__.update(cfg)

    def __call__(self, **cfg):
        return self.with_config(cfg)

    def with_config(self, cfg):
        rval = copy(self)
        rval.__dict__.update(cfg)
        return rval

    def __getattr__(self, attr):
        # Only triggers for attributes not in __dict__
        if attr.startswith("_"):
            return getattr(super(), attr)
        return None

    def __hrepr__(self, H, hrepr):
        return hrepr.stdrepr_object("Config", self.__dict__.items())


class HRepr:
    """
    Representation engine. This is the barebones engine. You should
    use/subclass StdHRepr, unless you want to start from scratch.
    """

    def __init__(self, accumulate_resources=True, **config):
        self.H = HTML()
        self.accumulate_resources = accumulate_resources
        self.consulted = set() if accumulate_resources else None
        self.resources = set()
        self.acquire_resources(self.global_resources)
        self.type_handlers = {**self.__default_handlers__()}
        self.type_handlers_resources = {}
        self.type_handlers_short = {**self.__default_handlers_short__()}
        self.config = Config(config)

    def __default_handlers__(self):
        return {}

    def __default_handlers_short__(self):
        return {}

    def __call__(self, obj, **cfg):
        """
        Return the HTML representation of an object.

        Args:
            obj: The object to represent
            cfg: Configuration to add to the current
                configuration for this operation.

        Returns:
            The representation of the object.
        """
        depth = self.config.depth or 0
        circular = self.config.circular or {None: None}
        seen_on_path = self.config.seen_on_path or frozenset()
        cfg.setdefault("depth", depth + 1)
        cfg["circular"] = circular
        cfg["seen_on_path"] = seen_on_path | {id(obj)}
        h = self.with_config(cfg)
        max_depth = h.config.max_depth

        if h.config.preprocess:
            obj = h.config.preprocess(obj, hrepr)

        if id(obj) in seen_on_path:
            # This object is a child of itself, so we display a neat
            # little loop to avoid busting the stack.
            n = circular.setdefault(id(obj), len(circular))
            result = self.H.span["hrepr-circular"](f"⥁", self.H.sub(n))

        else:
            if max_depth is not None and depth >= max_depth:
                result = h._hrepr(
                    obj,
                    self.type_handlers_short,
                    ["__hrepr_short__"],
                    self.stdrepr_short,
                )
            else:
                result = h._hrepr(
                    obj,
                    self.type_handlers,
                    ["__hrepr__", "__hrepr_short__"],
                    self.stdrepr,
                )

            if id(obj) in circular:
                result = self.H.div["circular_ref"](
                    result, self.H.span(circular[id(obj)])
                )

        if h.config.postprocess:
            return h.config.postprocess(obj, result, h.H, h) or result
        else:
            return result

    def with_config(self, cfg={}):
        h = copy(self)
        h.config = self.config.with_config(cfg)
        if h.config.type_handlers:
            h.type_handlers = {**h.type_handlers, **h.config.type_handlers}
        if h.config.type_handlers_short:
            h.type_handlers_short = {
                **h.type_handlers_short,
                **h.config.type_handlers_short,
            }
        if h.config.resources:
            if not isinstance(h.config.resources, (list, tuple)):
                h.config.resources = [h.config.resources]
            for res in h.config.resources:
                h.acquire_resources(res)
        return h

    def _hrepr(self, obj, type_handlers, method_names, std):
        root_cls = type(obj)
        handler = type_handlers.get(root_cls, None)

        if handler is None:
            if issubclass(root_cls, type):
                mro = [root_cls]
            else:
                mro = root_cls.mro()

            to_set = []
            for cls in mro:
                handler = type_handlers.get(cls, None)
                if handler is None:
                    for method_name in method_names:
                        handler = getattr(cls, method_name, None)
                        if handler:
                            break
                    if handler:
                        handler.resources = getattr(
                            cls, "__hrepr_resources__", None
                        )
                if handler:
                    for cls2 in to_set:
                        type_handlers[cls2] = handler
                    break
                to_set.append(cls)
            else:
                for cls2 in to_set:
                    type_handlers[cls2] = False

        if handler:
            res = getattr(handler, "resources", None)
            if self.consulted is not None and res is not None:
                self.acquire_resources(res)
            res = handler(obj, self.H, self)
            if res is not NotImplemented:
                return res
        else:
            return std(obj)

    def hrepr_with_resources(self, obj, **cfg):
        """
        This is equivalent to __call__, but performs the additional step of
        putting the set of resources required to properly display the object
        in the _resources property of the return value.
        """
        res = self(obj, **cfg)
        res.resources = self.resources
        return res

    def global_resources(self, H):
        """
        Resources required to properly display the default representations
        this HRepr instance produces. This method is meant to be subclassed.

        Returns:
            This implemention returns None.
        """
        return None

    def acquire_resources(self, source):
        """
        Store the resources returned by ``source()``. If ``source`` has
        been acquired before, it will not be called a second time.

        Args:
            source (callable): A function that returns a resource or a
                list of resources.

        Returns:
            None
        """
        if source not in self.consulted:
            self.consulted.add(source)
            if isinstance(source, Tag):
                res = source
            else:
                res = source(self.H)
            if res is None:
                res = set()
            elif isinstance(res, (list, tuple)):
                res = set(res)
            elif isinstance(res, Tag):
                res = {res}
            self.resources |= res

    def register(self, type, handler):
        """
        Register a pretty-printer for a type. This takes precedence
        on the type's ``__hrepr__`` method.

        Args:
            type (type): A data type.
            handler (function): A function with the same signature as
                ``__hrepr__`` methods: ``handler(obj, H, hrepr)``.
        """
        self.type_handlers[type] = handler

    def register_all(self, handlers):
        """
        Register pretty-printers for many types. This is equivalent to:

            for type, handler in handlers.items():
                self.register(type, handler)
        """
        self.type_handlers.update(handlers)

    def stdrepr(self, obj, *, cls=None, tag="span"):
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
        return getattr(self.H, tag)[cls](str(obj))

    def stdrepr_short(self, obj, *, cls=None, tag="span"):
        """
        Standard short representation for objects, used for objects at
        a depth that exceeds ``hrepr_object.config.max_depth``. That
        representation is just the object's type between ``<>``s, e.g.
        ``<MyClass>``.

        This behavior can be overriden with a ``__hrepr_short__`` method
        on the object, or an entry in ``hrepr_object.type_handlers_short``.

        Args:
            obj: The object to represent.
            cls (optional): The class name for the representation. If None,
                stdrepr will use ``'hrepr-' + obj.__class__.___name__``
            tag (optional): The tag for the representation, defaults to
                'span'.
        """
        cls_name = obj.__class__.__name__
        if cls is None:
            cls = f"hrepr-short-{cls_name}"
        return getattr(self.H, tag)[cls](f"<{cls_name}>")

    def stdrepr_iterable(self, obj, *, cls=None, before=None, after=None):
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
            cls = f"hrepr-{obj.__class__.__name__}"
        children = [self(a) for a in obj]
        return self.titled_box((before, after), children, "h", "h")[cls]

    def stdrepr_object(
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
            elements: A list of (key, value) pairs, which will be
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
                kv = H.div["hrepr-object-kvpair"](
                    wrap(k), delimiter or "", self(v)
                )
                contents.append(kv)
        else:
            t = H.table()["hrepr-object-table"]
            for k, v in elements:
                tr = H.tr(H.td(wrap(k)))
                if delimiter is not None:
                    tr = tr(H.td["hrepr-delimiter"](delimiter))
                tr = tr(H.td(self(v)))
                # t = t(H.tr(H.td(wrap(k)), H.td(self(v))))
                t = t(tr)
            contents = [t]

        title_brackets = isinstance(title, tuple) and len(title) == 2
        horizontal = short or title_brackets

        rval = self.titled_box(
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


#########################################
# Handlers for standard data structures #
#########################################


def handler_scalar(obj, H, hrepr):
    return hrepr.stdrepr(obj)


def handler_list(obj, H, hrepr):
    return hrepr.stdrepr_iterable(obj, before="[", after="]")


def handler_tuple(obj, H, hrepr):
    return hrepr.stdrepr_iterable(obj, before="(", after=")")


def handler_set(obj, H, hrepr):
    return hrepr.stdrepr_iterable(obj, before="{", after="}")


def handler_frozenset(obj, H, hrepr):
    return hrepr.stdrepr_iterable(obj, before="{", after="}")


def handler_dict(obj, H, hrepr):
    return hrepr.stdrepr_object(
        ("{", "}"),
        list(obj.items()),
        cls="hrepr-dict",
        quote_string_keys=True,
        short=hrepr.config.mapping_layout == "h",
    )


def handler_bool(obj, H, hrepr):
    if obj is True:
        return H.span["hrepr-True", "hrepr-bool"]("True")
    else:
        return H.span["hrepr-False", "hrepr-bool"]("False")


def handler_bytes(obj, H, hrepr):
    return hrepr.stdrepr(obj.hex(), cls="hrepr-bytes")


def handler_Tag(obj, H, hrepr):
    """
    Returns the default representation for a tag, which is the tag itself.
    """
    return obj


########################
# Short handlers … ⋯ ⋮ #
########################


def _ellipsis(H, hrepr, open, close, ellc="…"):
    ell = H.span["hrepr-ellipsis"](ellc)
    return hrepr.titled_box((open, close), [ell])


def handler_short_str(s, H, hrepr):
    max_length = 20
    if len(s) > max_length:
        s = s[: max_length - 1] + "…"
    return hrepr.stdrepr(s)


def handler_short_list(obj, H, hrepr):
    if len(obj) == 0:
        return handler_list(obj, H, hrepr)
    return _ellipsis(H, hrepr, "[", "]")["hrepr-list"]


def handler_short_tuple(obj, H, hrepr):
    if len(obj) == 0:
        return handler_tuple(obj, H, hrepr)
    return _ellipsis(H, hrepr, "(", ")")["hrepr-tuple"]


def handler_short_set(obj, H, hrepr):
    if len(obj) == 0:
        return handler_set(obj, H, hrepr)
    return _ellipsis(H, hrepr, "{", "}")["hrepr-set"]


def handler_short_frozenset(obj, H, hrepr):
    if len(obj) == 0:
        return handler_frozenset(obj, H, hrepr)
    return _ellipsis(H, hrepr, "{", "}")["hrepr-frozenset"]


def handler_short_dict(obj, H, hrepr):
    if len(obj) == 0:
        return handler_dict(obj, H, hrepr)
    return _ellipsis(H, hrepr, "{", "}", "⋮")["hrepr-dict"]


class StdHRepr(HRepr):
    """
    Standard representation engine. Includes representations for
    `list, tuple, set, frozenset, dict, Tag`.
    """

    def __default_handlers__(self):
        return {
            list: handler_list,
            tuple: handler_tuple,
            set: handler_set,
            frozenset: handler_frozenset,
            dict: handler_dict,
            bool: handler_bool,
            bytes: handler_bytes,
            Tag: handler_Tag,
        }

    def __default_handlers_short__(self):
        return {
            int: handler_scalar,
            float: handler_scalar,
            str: handler_short_str,
            bytes: handler_short_str,
            list: handler_short_list,
            tuple: handler_short_tuple,
            set: handler_short_set,
            frozenset: handler_short_frozenset,
            dict: handler_short_dict,
            bool: handler_bool,
            type(None): handler_scalar,
        }

    def global_resources(self, H):
        """
        Returns a ``<style>`` tag that contains a stylesheet to style numbers,
        strings, lists, and so on. The stylesheet is in the file
        ``../style/hrepr.css`` relative to this one.

        If you override this in a subclass, remember to include the basic
        resources, like this for example (assuming my_resources is a set):

        ``return my_resources | super().global_resources(H)``
        """
        return {H.style(css_hrepr)}


def hrepr(obj, **config):
    """
    Return a Tag that represents the given object. The result can be converted
    to HTML with ``str(result)``, or ``str(result.as_page())``. It can also
    be printed, or displayed in a Jupyter Notebook.

    The config keyword arguments don't do anything in the default
    implementation, but they can be accessed from the ``hrepr`` argument
    to ``__hrepr__``, as ``hrepr.config``, so custom representations for
    objects are free to use them.
    """
    return StdHRepr(**config).hrepr_with_resources(obj)
