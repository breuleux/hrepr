from dataclasses import dataclass

from hrepr import pprint


class Person:
    def __init__(self, name, age, job):
        self.name = name
        self.age = age
        self.job = job

    def __hrepr__(self, H, hrepr):
        # H.instance is a special kind of tag to format data like an instance.
        # Notice how we call the hrepr parameter on self.age and self.job to
        # format them.
        return H.instance["person"](
            H.pair("age", hrepr(self.age), delimiter=" ↦ "),
            H.pair("job", hrepr(self.job), delimiter=" ↦ "),
            # The "type" represents the header for the "instance"
            type=self.name,
        )

    def __hrepr_short__(self, H, hrepr):
        # H.atom is really mostly like H.span, but the textual representation
        # of H.atom(x) through pprint is "x" whereas H.span(x) would be
        # "<span>x</span>".
        return H.atom["person-short"](self.name)


class MyList(list):
    def __hrepr__(self, H, hrepr):
        # Also works nicely with the HTML representation, except that the
        # delimiter is ignored
        return H.bracketed(
            start="<{", end="}>", delimiter=" | ", *map(hrepr, self)
        )


@dataclass
class Point:
    x: int
    y: int


if __name__ == "__main__":

    def title(text):
        print()
        print(text)
        print("=" * len(text))
        print()

    title("Basic usage")

    obj = {
        "lists": [1, 2, 3.14159],
        "tuples": (True, False),
        "dataclasses": Point(10, 20),
        "null": None,
    }
    pprint(obj)

    title("Recursive data structures")
    rec = dict(obj)
    rec["recursive"] = rec
    pprint(rec)

    title("Custom objects")
    amelia = Person(name="Amelia", age=35, job="gardener")
    pprint(amelia)
    pprint(amelia, max_col=10)
    pprint(amelia, max_depth=0)
    pprint([amelia, amelia, amelia], shortrefs=True)

    title("Custom lists")
    li = MyList([1, 2, 3, 4])
    pprint(li)
    pprint(li, max_col=10)
