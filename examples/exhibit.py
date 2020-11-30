# Redirect output to a HTML file and view it in your browser

import json
import math
from dataclasses import dataclass

from ovld import has_attribute

from hrepr import H, Hrepr, hrepr


@dataclass
class Point:
    x: int
    y: int


class Color:
    def __init__(self, r, g, b):
        self.r = r
        self.g = g
        self.b = b

    def __hrepr__(self, H, hrepr):
        size = hrepr.config.swatch_size or 25
        style = f"""
        background: rgb({self.r}, {self.g}, {self.b});
        width: {size}px;
        height: {size}px;
        margin: 3px;
        """
        return H.div(style=style)


class Person:
    def __init__(self, name, age, job):
        self.name = name
        self.age = age
        self.job = job

    @classmethod
    def __hrepr_resources__(cls, H):
        # Note: you might need to add "!important" next to some rules if
        # they conflict with defaults from hrepr's own CSS.
        return H.style(
            """
            .person {
                background: magenta !important;
                border-color: magenta !important;
            }
            .person-short { font-weight: bold; color: green; }
            """
        )

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


class MyMixin(Hrepr):
    # Change the representation of integers

    def hrepr_resources(self, cls: int):
        # Note: in hrepr_resources, cls is the int type, not an integer
        return self.H.style(".my-integer { color: fuchsia; }")

    def hrepr(self, n: int):
        return self.H.span["my-integer"]("The number ", str(n))

    def hrepr_short(self, n: int):
        return self.H.span["my-integer"](str(n))

    # Specially handle any object with a "quack" method

    def hrepr_short(self, duck: has_attribute("quack")):
        # Note: if there is no hrepr it falls back to hrepr_short
        return self.H.span("🦆")


hlstyle = H.style(".highlight { border: 3px solid red !important; }")


def highlight(x):
    def postprocess(element, obj, hrepr):
        if obj == x:
            # Adds the "highlight" class and attaches a style
            return element["highlight"].fill(resources=hlstyle)
        else:
            return element

    return postprocess


class Farfetchd:
    def quack(self):
        return "DUX"


class Plot:
    def __init__(self, data):
        self.data = data

    @classmethod
    def __hrepr_resources__(cls, H):
        return H.require(
            name="plotly", src="https://cdn.plot.ly/plotly-latest.min.js",
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


cystyle = """
    {
      selector: 'node',
      style: {
        'background-color': '#800',
        'label': 'data(id)'
      }
    },

    {
      selector: 'edge',
      style: {
        'width': 3,
        'line-color': '#ccc',
        'target-arrow-color': '#ccc',
        'target-arrow-shape': 'triangle',
        'curve-style': 'bezier'
      }
    }
"""


class Graph:
    def __init__(self, *edges):
        self.edges = edges
        self.nodes = {src for src, _ in edges} | {tgt for _, tgt in edges}

    @classmethod
    def __hrepr_resources__(cls, H):
        return H.require(
            name="cytoscape",
            src="https://cdnjs.cloudflare.com/ajax/libs/cytoscape/3.17.0/cytoscape.min.js",
        )

    def __hrepr__(self, H, hrepr):
        width = hrepr.config.graph_width or 500
        height = hrepr.config.graph_height or 500
        data = [{"data": {"id": node}} for node in self.nodes]
        data += [
            {"data": {"source": src, "target": tgt}} for src, tgt in self.edges
        ]
        return H.script(
            f"""
            cydiv.style.width = "{width}px";
            cydiv.style.height = "{height}px";
            cytoscape({{
                container: cydiv,
                elements: {json.dumps(data)},
                style: [{cystyle}],
                layout: {{name: 'cose'}}
            }});
            """,
            require="cytoscape",
            create_div="cydiv",
        )


if __name__ == "__main__":

    entries = []

    def hprint(*objs, **kwargs):
        entries.append(hrepr(*objs, **kwargs))

    def title(x):
        entries.append(H.h2(x))

    def subtitle(x):
        entries.append(H.h4(x))

    title("Basic usage")
    obj = {
        "lists": [1, 2, 3.14159],
        "tuples": (True, False),
        "dataclasses": Point(10, 20),
        "null": None,
    }
    hprint(obj)

    subtitle("Setting max_depth=1")
    hprint(obj, max_depth=1)

    subtitle("Recursive data structures")
    rec = dict(obj)
    rec["recursive"] = rec
    hprint(rec)

    subtitle("A list of three of the same object")
    amelia = Person(name="Amelia", age=35, job="gardener")
    hprint([amelia, amelia, amelia])

    subtitle("Same, but shortrefs=True")
    hprint([amelia, amelia, amelia], shortrefs=True)

    subtitle("Same, but norefs=True")
    hprint([amelia, amelia, amelia], norefs=True)

    title("Custom representation")
    colors = [Color(i * 32, 0, 0) for i in range(9)]
    hprint(colors)

    subtitle("Varying configuration values")
    hprint(colors, swatch_size=50)

    subtitle("Without a mixin")
    dux = Farfetchd()
    things = [1, 2, dux, 4, dux]
    hprint(things)

    subtitle("With a custom mixin")
    hprint(things, mixins=MyMixin)

    subtitle("Playing with max_depth")
    hprint(things, mixins=MyMixin, max_depth=1)

    subtitle("Use a postprocessor to highlight the number 2")
    hprint([1, 2, [3, [2.0], "2"]], postprocess=highlight(2))

    title("Cool stuff")

    subtitle("Plot with plotly")
    hprint(Plot([math.sin(x / 10) for x in range(100)]))

    subtitle("Graph with cytoscape")
    g1 = Graph(("A", "B"), ("B", "A"), ("A", "C"), ("C", "D"), ("D", "E"))
    g2 = Graph(("Rock", "Scissors"), ("Scissors", "Paper"), ("Paper", "Rock"))
    hprint(
        [g1, g2], graph_width=300, graph_height=300,
    )

    pg = hrepr.page(*entries)
    print(pg)
