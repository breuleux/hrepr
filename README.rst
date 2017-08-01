hrepr
=====

``hrepr`` is a package to create an HTML representation for Python
objects. It can output to Jupyter Notebooks and it can also generate
standalone pages with the representation of choice objects.

Install
-------

``hrepr`` requires at least Python 3.6

.. code:: bash

    $ pip3 install hrepr

Usage
-----

.. code:: python

    from hrepr import hrepr
    obj = {'potatoes': [1, 2, 3], 'bananas': {'cantaloups': 8}}

    # Print the HTML representation of obj
    print(hrepr(obj))

    # Wrap the representation in <html><body> tags and embed the default
    # css style files to produce a standalone page.
    print(hrepr(obj).as_page())

In a Jupyter Notebook, return ``hrepr(obj)`` directly.

Custom representations
----------------------

A custom representation for an object can be defined using the
``__hrepr__`` method on the object, and if necessary, an
``__hrepr_resources__`` method on the class. No dependency on ``hrepr``
is necessary:

.. code:: python

    class RedGreen:
        def __init__(self, r, g):
            self.r = r
            self.g = g

        @classmethod
        def __hrepr_resources__(cls, H):
            return H.style('''
            .red { background-color: red; }
            .green { background-color: green; }
            ''')

        def __hrepr__(self, H, hrepr):
            return H.div(
                H.div['red'](hrepr(self.r)),
                H.div['green'](hrepr(self.g))
            )

``__hrepr__`` receives two arguments:

-  ``H`` is the HTML builder, which has the simple interface:
   ``H.tag['klass', ...](child, ..., attr=value, ...)`` to create the
   tag ``<tag class=klass attr=value>child</tag>``. You can add more
   classes, attributes and children, i.e. it is legal to write
   ``H.a['cls1'](href='blah')['cls2']('hello', attr=value)``

   -  Use ``H.raw(string)`` to insert an unescaped string (e.g. literal
      HTML)
   -  Use ``H.inline(...)`` to concatenate the children without wrapping
      them in a tag.

-  ``hrepr`` is a function that can be called recursively to get the
   representation of the object's fields.

``__hrepr_resources__`` is optional, but if it is defined, it should
return one or a list of tags that should be inserted in the ``<head>``
section of the page in order to properly format the representation.
These can be ``<style>`` tags, ``<script>`` tags, or ``<link>`` tags.

Custom hrepr
------------

You can also customize the ``hrepr`` function by subclassing the
``HRepr`` or ``StdHRepr`` classes (the difference between the two is
that the latter defines default representations for several Python types
like ``list`` or ``dict`` whereas the former does not).

Your subclass can override the following functions and fields:

-  **``global_resources(H)``** should return one or a list of tags to
   insert in ``<head>``.
-  **``__default_handlers__()``** should return a dict that associates types to
   handlers with the signature ``handler(obj, H, hrepr)``. When given
   an object of a certain type, hrepr will look for it there first.
-  **``__call__(obj)``** is the main representation function, and will be
   called recursively for every object to represent.

.. code:: python

    from hrepr import StdHRepr

    class MyRepr(StdHRepr):
        def __default_handlers__(self):
            return {int: self.repr_int}

        def global_resources(self, H):
            return H.style(".my-integer { color: fuchsia; }")

        def repr_int(self, n, H, hrepr):
            return H.span['my-integer']('The number ', str(n))

    def myrepr(obj):
        # Call hrepr_with_resources to attach the resources to the
        # return value, otherwise .as_page() will not work as
        # intended.
        return MyRepr().hrepr_with_resources(obj)

    print(myrepr(10)) # <span class="my-integer">The number 10</span>
    print(myrepr(10).as_page()) # This will include the style
