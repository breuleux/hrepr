
from .h import Tag, HTML, css_hrepr


class HRepr:
    """
    Representation engine. This is the barebones engine. You should
    use/subclass StdHRepr, unless you want to start from scratch.
    """

    def __init__(self, accumulate_resources=True, **config):
        self.H = HTML()
        self.consulted = set() if accumulate_resources else None
        self.resources = set()
        self.acquire_resources(self.global_resources)
        self.config = config

    def __call__(self, obj):
        """
        Return the HTML representation of an object.

        Args:
            obj: The object to represent

        Returns:
            The representation of the object.
        """
        selfmethod = f'repr_{obj.__class__.__name__}'
        if hasattr(self, selfmethod):
            res = getattr(self, selfmethod)(obj)
            if res is not NotImplemented:
                return res

        if self.consulted is not None and hasattr(obj, '__hrepr_resources__'):
            method = obj.__hrepr_resources__
            self.acquire_resources(method)
        if hasattr(obj, '__hrepr__'):
            return obj.__hrepr__(self.H, self)
        else:
            return self.stdrepr(obj)

    def hrepr_with_resources(self, obj):
        """
        This is equivalent to __call__, but performs the additional step of
        putting the set of resources required to properly display the object
        in the _resources property of the return value.
        """
        res = self(obj)
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
            res = source(self.H)
            if res is None:
                res = set()
            elif isinstance(res, (list, tuple)):
                res = set(res)
            elif isinstance(res, Tag):
                res = {res}
            self.resources |= res

    def stdrepr(self, obj, *, cls=None, tag='span'):
        """
        Standard representation for objects, used when there is no
        repr_<classname> method on the HRepr object, and no __hrepr__
        method on obj. For an object of class 'klass', the result is:

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
            cls = f'hrepr-{obj.__class__.__name__}'
        return getattr(self.H, tag)[cls](str(obj))

    def stdrepr_iterable(self, obj, *,
                         cls=None, tag='div',
                         before=None, after=None, separator=None):
        """
        Helper function to represent iterables. StdHRepr calls this on
        lists, tuples, sets and frozensets, but NOT on iterables in general.
        This method may be called to produce custom representations.

        When called on a list ``[a, b, ...]`` this is roughly:

        ``<div class="hrepr-list">{self(a)}{self(b)}</div>``

        Where ``{self(a)}`` etc. is the representation of the elements in
        the iterable.

        Args:
            obj (iterable): The iterable to represent.
            cls (optional): The class name for the representation. If None,
                stdrepr will use ``'hrepr-' + obj.__class__.___name__``
            tag (optional): The tag for the representation, defaults to
                'div'. Set to None to directly inline the element's hreprs.
            before (optional): A string or a Tag to prepend to the elements.
            after (optional): A string or a Tag to append to the elements.
            separator (optional): A string or a Tag that will be inserted
                between each element to separate them.
        """
        if cls is None:
            cls = f'hrepr-{obj.__class__.__name__}'

        children = [self(a) for a in obj]
        if separator is not None:
            children = children[:1] + [[separator, c] for c in children[1:]]
        if before is not None:
            children = [before, *children]
        if after is not None:
            children.append(after)

        if tag is None:
            return Tag(None, {}, children)
        else:
            return getattr(self.H, tag)[cls](children)


class StdHRepr(HRepr):
    """
    Standard representation engine. Includes representations for
    `list, tuple, set, frozenset, dict, Tag`.
    """

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

    def repr_list(self, obj):
        return self.stdrepr_iterable(obj, before='[', separator=', ', after=']')

    def repr_tuple(self, obj):
        return self.stdrepr_iterable(obj, before='(', separator=', ', after=')')

    def repr_set(self, obj):
        return self.stdrepr_iterable(obj, before='{', separator=', ', after='}')

    def repr_frozenset(self, obj):
        return self.stdrepr_iterable(obj, before='{', separator=', ', after='}')

    def repr_dict(self, obj):
        rows = [self.H.tr(self.H.td(self(k), self.H.td(self(v))))
                for k, v in obj.items()]
        return self.H.table['hrepr-dict'](*rows)

    def repr_bool(self, obj):
        if obj is True:
            return self.H.span['hrepr-True', 'hrepr-bool']("True")
        else:
            return self.H.span['hrepr-False', 'hrepr-bool']("False")

    def repr_Tag(self, obj):
        """
        Returns the default representation for a tag, which is the tag itself.
        """
        return obj


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

