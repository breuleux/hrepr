# hrepr

`hrepr` outputs HTML/pretty representations for Python objects.

✅ Nice, colourful representations of lists, dicts, dataclasses, booleans...<br/>
✅ Ridiculously extensible and configurable<br/>
✅ Handles recursive data structures<br/>
✅ Compatible with Jupyter notebooks<br/>
✅ Also pretty-prints to the terminal<br/>

<img src="images/hrepr1.png" width="400px"><img src="images/hrepr2.png" width="400px">

See `examples/Basics.ipynb` and `examples/Advanced.ipynb` for more examples, but keep in mind that GitHub can't display them properly.


## Install

```python
pip install hrepr
```


## Usage

```python
from hrepr import hrepr
obj = {'potatoes': [1, 2, 3], 'bananas': {'cantaloups': 8}}

# Print the HTML representation of obj
print(hrepr(obj))

# Wrap the representation in <html><body> tags and embed the default
# css style files in a standalone page, which is saved to obj.html
hrepr.page(obj, file="obj.html")
```

In a Jupyter Notebook, you can return `hrepr(obj)` from any cell and it will show its representation for you. You can also write `display_html(hrepr(obj))`.


## Custom representations

A custom representation for an object can be defined using the following three methods (it is not necessary to define all of them, only those that are relevant to your case):

* `__hrepr__(self, H, hrepr)` returns the normal HTML representation.
    * Use `H.span["some-class"](some-content, some_attr=some_value)` to generate HTML.
    * Use `hrepr(self.x)` to generate the representation for some subfield `x`.
    * `hrepr.config` contains any keyword arguments given in the top level call to `hrepr`. For instance, if you call `hrepr(obj, blah=3)`, then `hrepr.config.blah == 3` in all calls to `__hrepr__` down the line (the default value for all keys is `None`).
* `__hrepr_short__(self, H, hrepr)` returns a *short* representation, ideally of a constant size.
    * The output of this method is used when we hit max depth, or for repeated references.
    * Only include bare minimum information. Short means short.
* `__hrepr_resources__(cls, H)` is a **classmethod** that returns resources common to all instances of the class (typically a stylesheet or a script).
    * When generating a page, the resources will go in `<head>`.
    * You can return a list of resources.

No dependency on `hrepr` is necessary.

For example:

```python
class Person:
    def __init__(self, name, age, job):
        self.name = name
        self.age = age
        self.job = job

    @classmethod
    def __hrepr_resources__(cls, H):
        # Note: you might need to add "!important" next to some rules if
        # they conflict with defaults from hrepr's own CSS.
        return H.style("""
            .person {
                background: magenta !important;
                border-color: magenta !important;
            }
            .person-short { font-weight: bold; color: green; }
        """)

    def __hrepr__(self, H, hrepr):
        # H.instance is a special kind of tag to format data like an instance.
        # Notice how we call the hrepr parameter on self.age and self.job to
        # format them.
        return H.instance["person"](
            H.pair("age", hrepr(self.age), delimiter=" ↦ "),
            H.pair("job", hrepr(self.job), delimiter=" ↦ "),
            # The "type" represents the header for the "instance"
            type=self.name,
            # "vertical=True" means we'll display the pairs as a table with
            # the delimiters aligned, instead of sticking them horizontally
            # next to each other
            vertical=True,
        )

    def __hrepr_short__(self, H, hrepr):
        # H.atom is really mostly like H.span, but the textual representation
        # of H.atom(x) through pprint is "x" whereas H.span(x) would be 
        # "<span>x</span>".
        return H.atom["person-short"](self.name)
```

<img src="images/hrepr3.png" width="600px">

Note how this also gave us a textual representation *for free*, using `hrepr.pprint`. This feature requires using special tags like `H.instance`, `H.bracketed`, `H.pair` or `H.atom` -- other ones will pretty-print like HTML -- but it's neat regardless!


## References

`hrepr` (and `hrepr.pprint` for that matter) can handle circular references. Furthermore, if an object is found at several places in a structure, only the first occurrence will be printed in full, and any other will be a numeric reference mapped to the short representation for the object. It looks like this:

<img src="images/hrepr4.png" width="600px">

The `shortrefs` and `norefs` configuration keys control the representation of references:

<img src="images/hrepr5.png" width="600px">

`norefs` is ignored when there are circular references.


## HTML generation

Generate HTML using the `H` parameter to `__hrepr__`, or import it and use it directly:

```python
from hrepr import H
html = H.span["bear"](
    "Only ", H.b("YOU"), " can prevent forest fires!",
    style="color: brown;"
)
print(html)
# <span class="bear" style="color: brown;">Only <b>YOU</b> can prevent forest fires!</span>
```

`H` can be built incrementally: if you have an element, you can call it to add children, index it to add classes, and so on. For instance:

```python
from hrepr import H
html = H.span()
html = html("Only ")
html = html(style="color: brown;")["bear"]
html = html(H.b("YOU"), " can prevent forest fires!")
print(html)
# <span class="bear" style="color: brown;">Only <b>YOU</b> can prevent forest fires!</span>
```

This can be handy if you want to tweak generated HTML a little. For example, `hrepr(obj)["fox"]` will tack on the class `fox` to the representation of the object.


### Special tags

Standard tags like `H.span`, `H.div`, `H.strong`, etc. are handled according to standards. But there are some special tags which are postprocessed by the hrepr "backend". The HTML backend will reduce them to standard tags, whereas the pprint backend will display them like Python data structures.

* `H.instance(*children, type=<str>, delimiter=<str>, short=<bool>, horizontal=<bool>, vertical=<bool>)`
    * Represents some kind of object
    * `type`: the name of the object (or class name)
        * It is not *necessarily* a string, it can also be a tag.
    * `delimiter`: the delimiter between elements, defaults to a comma. The HTML formatter ignores this.
    * `short/horizontal/vertical`: the layout/style
* `H.bracketed(*children, type=<str>, open=<str>, close=<str>, delimiter=<str>, short=<bool>, horizontal=<bool>, vertical=<bool>)`
    * `type`: the name of the object (or class name), which is NOT displayed. Instead, the class `hreprt-<name>` is given to the element.
    * `open/close`: the opening and closing brackets.
    * `delimiter`: the delimiter between elements, defaults to a comma. The HTML formatter ignores this.
    * `short/horizontal/vertical`: the layout/style. Lists use horizontal, dicts use vertical, and the short representations use short.
* `H.pair(x, y, delimiter=<str>)`: a key -> value mapping. They are handled specially inside of `bracketed` and `instance` so that the delimiters are aligned.
* `H.atom(element, type=<str>)`: essentially equivalent to `H.span["hreprt-<type>"](element)`, or `repr(element)` for pprint.


### Script tags

To make it a bit easier to include and use JavaScript libraries, there is `H.require` and a small extension to `H.script`:

* `H.require(name=<str>, src=<path>)` declares an import of the script at the given path (you can use a CDN link) and exports it under the given name.
* `H.script(<code>, require=<str/list>, create_div=<str>)` will first wait for the modules given in `require` to be loaded (use the names declared in `H.require`).
    * If `create_div` is given a name, a `div` will be auto-generated with a unique ID, inserted just above the script tag, and will be stored in the variable with the given name, so you can do something with it in the script.

Here's an example using Plotly:

```python
import json

class Plot:
    def __init__(self, data):
        self.data = data

    @classmethod
    def __hrepr_resources__(cls, H):
        return H.require(
            name="plotly",
            src="https://cdn.plot.ly/plotly-latest.min.js",
        )

    def __hrepr__(self, H, hrepr):
        data = {
            "x": list(range(len(self.data))),
            "y": list(self.data),
        }
        return H.script(
            f"plotly.newPlot(plotdiv, [{json.dumps(data)}]);",
            require="plotly",
            create_div="plotdiv",
        )
```

And just like that:

<img src="images/hrepr6.png" width="600px">


## Customize hrepr

### Mixins

If you want to *really* customize hrepr, you can use mixins. They look like a bit of black magic, but they're simple enough:

```python
# ovld is one of the dependencies of hrepr
from ovld import ovld, has_attribute
from hrepr import hrepr, Hrepr

class MyMixin(Hrepr):
    # Change the representation of integers

    def hrepr_resources(self, cls: int):
        # Note: in hrepr_resources, cls is the int type, not an integer
        return self.H.style(".my-integer { color: fuchsia; }")

    def hrepr(self, n: int):
        return self.H.span["my-integer"]("The number ", str(n))

    # Specially handle any object with a "quack" method

    def hrepr(self, duck: has_attribute("quack")):
        return self.H.span("🦆")
```

<img src="images/hrepr7.png" width="600px">

The annotation for a rule can either be a type, `ovld.has_attribute`, or pretty much any function wrapped with the `ovld.meta` decorator. See the documentation for [ovld](https://github.com/breuleux/ovld#other-features) for more information.

And yes, you can define `hrepr` multiple times inside the class, as long as they have distinct annotations and you inherit from `Hrepr`. You can also define `hrepr_short` or `hrepr_resources` the same way.

### Postprocessors

`hrepr` can be given a postprocessor that is called on the representation of any object. You can use this to do things like highlighting specific objects:

```python
from hrepr import H

style = H.style(".highlight { border: 3px solid red !important; }")

def highlight(x):
    def postprocess(element, obj, hrepr):
        if obj == x:
            # Adds the "highlight" class and attaches a style
            return element["highlight"].fill(resources=style)
        else:
            return element

    return postprocess

hrepr([1, 2, [3, 4, 2]], postprocess=highlight(2))
```

<img src="images/hrepr8.png" width="600px">
