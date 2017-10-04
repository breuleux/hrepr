hrepr
=====

``hrepr`` is a package to create an HTML representation for Python
objects. It can output to Jupyter Notebooks and it can also generate
standalone pages with the representation of choice objects.

.. image:: https://github.com/breuleux/hrepr/raw/master/images/hrepr1.png

.. image:: https://github.com/breuleux/hrepr/raw/master/images/hrepr2.png

See the ``examples.ipynb`` notebook for more examples, but keep in mind that
GitHub doesn't display it properly.

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

``__hrepr_short__`` is also optional, and should return a representation
that has a constant (small) size, e.g. the value of a class's ``name``
field, the length of the array, or something or other.

Configure the representation
----------------------------

``hrepr`` can take an arbitrary number of keyword arguments. Some of them are
treated specially, whereas others are stashed in the ``hrepr`` object passed to
``__hrepr__`` methods and may be used to implement custom display options on
custom elements. The following keys are special (examples of their use can
be found in the ``examples.ipynb`` notebook):

- **max_depth** limits how many layers of nested objects will be displayed.
  Past that depth, objects are represented with their ``__hrepr_short__``
  method.

- **type_handlers** maps one or more types to functions with signature
  ``(obj, H, hrepr) -> Tag`` which are used to generate the HTML structure to
  display. These handlers override ``__hrepr__``.

- **type_handlers_short**: same, but for short representations.

- **resources** is one or a list of functions with signature ``(H,) -> [Tag]``,
  meaning that they take the ``H`` constructor and return one or more ``style``
  or ``script`` or ``link`` tags that are globally needed.

- **preprocess** is a function with signature ``(obj, hrepr) -> obj``. It
  must return an alternative object to display instead of ``obj``.

- **postprocess** is a function with signature ``(obj, tag, H, hrepr) -> Tag``.
  It must return an alternative or modified ``Tag`` object to display. For
  example, it could return ``tag['highlight']`` which is the syntax to add
  the ``'highlight'`` class to a ``Tag``, in which case the postprocessor
  is ostensibly highlighting the corresponding object. If the postprocessor
  returns ``None``, the object will be represented by ``tag``, as it would
  be if there was no postprocessor.

Custom hrepr
------------

You can also customize the ``hrepr`` function by subclassing the
``HRepr`` or ``StdHRepr`` classes (the difference between the two is
that the latter defines default representations for several Python types
like ``list`` or ``dict`` whereas the former does not).

Your subclass can override the following functions and fields:

-  ``global_resources(H)`` should return one or a list of tags to
   insert in ``<head>``.
-  ``__default_handlers__()`` should return a dict that associates types to
   handlers with the signature ``handler(obj, H, hrepr)``. When given
   an object of a certain type, hrepr will look for it there first.
-  ``__call__(obj)`` is the main representation function, and will be
   called recursively for every object to represent.

.. code:: python

    from hrepr import StdHRepr

    class MyRepr(StdHRepr):
        def __default_handlers__(self):
            dh = super().__default__handlers__()
            return {**dh, int: self.repr_int}

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
