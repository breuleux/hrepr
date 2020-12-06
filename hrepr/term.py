from ovld import ovld

from .h import H, Tag
from .textgen import Breakable, Sequence, Text, join


@ovld
def standard_terminal(self, node: Tag):
    """Generate a terminal representation."""
    return node.text_parts()


@ovld
def standard_terminal(self, node: type(H.atom)):
    typ = node.get_attribute("type", None)
    if typ == "str":
        (child,) = node.children
        return Text(repr(child))
    else:
        return Text("".join(map(str, node.children)))


@ovld
def standard_terminal(self, node: type(H.defn)):
    key, name = node.children
    return Text(f"{key} {name}")


@ovld
def standard_terminal(self, node: type(H.pair)):
    delim = node.get_attribute("delimiter", ": ")
    k, v = node.children
    return Sequence(self(k), delim, self(v))


@ovld
def standard_terminal(self, node: type(H.bracketed)):
    start = node.get_attribute("start", "(")
    end = node.get_attribute("end", ")")
    delim = node.get_attribute("delimiter", ", ")
    return Breakable(
        start=start, body=join(map(self, node.children), delim), end=end,
    )


@ovld
def standard_terminal(self, node: type(H.instance)):
    typ = node.get_attribute("type", "<object>")
    delim = node.get_attribute("delimiter", ", ")
    start = node.get_attribute("start", "(")
    end = node.get_attribute("end", ")")
    return Breakable(
        start=Sequence(self(typ), start),
        body=join(map(self, node.children), delim),
        end=end,
    )


@ovld
def standard_terminal(self, node: type(H.ref)):
    num = node.get_attribute("num", -1)
    ref = Sequence("#", str(num))
    if node.children:
        return Sequence(ref, "=", *map(self, node.children))
    else:
        return ref


@ovld
def standard_terminal(self, node: object):
    return str(node)
