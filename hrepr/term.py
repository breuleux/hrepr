from types import SimpleNamespace

from ovld import ovld

from .h import H, Tag


def ensure_text(x):
    if isinstance(x, str):
        return Text(x)
    else:
        return x


def join(seq, sep):
    *first, last = seq
    return [Sequence(x, sep) for x in first] + [last]


class TerminalPrinter:
    def __len__(self):
        return self.len

    def __str__(self):
        value, offset = self.format(tabsize=4, max_col=80, offset=0)
        return value


class Breakable(TerminalPrinter):
    def __init__(self, start, body, end):
        self.start = ensure_text(start)
        self.body = list(map(ensure_text, body))
        self.end = ensure_text(end)
        self.len = len(self.start) + sum(map(len, self.body)) + len(self.end)

    def format(
        self, tabsize=4, offset=0, line_offset=0, max_col=80, compact=False
    ):
        s = ""
        if compact or offset + len(self) <= max_col:
            if self.start is not None:
                value, offset = self.start.format(compact=True, offset=offset)
                s += value
            for x in self.body:
                value, offset = x.format(compact=True, offset=offset)
                s += value
            if self.end is not None:
                value, offset = self.end.format(compact=True, offset=offset)
                s += value
            return s, offset
        else:
            if self.start is not None:
                value, offset = self.start.format(
                    tabsize=tabsize,
                    offset=offset,
                    line_offset=line_offset,
                    max_col=max_col,
                )
                s += value

            for x in self.body:
                ind = line_offset + tabsize
                value, offset = x.format(
                    tabsize=tabsize,
                    offset=ind,
                    line_offset=ind,
                    max_col=max_col,
                )
                s += "\n" + (ind * " ") + value

            if self.end is not None:
                value, offset = self.end.format(
                    tabsize=tabsize,
                    offset=offset,
                    line_offset=line_offset,
                    max_col=max_col,
                )
                s += "\n" + (line_offset * " ") + value

            return s, offset


class Sequence(TerminalPrinter):
    def __init__(self, *elements):
        self.elements = [Text(e) if isinstance(e, str) else e for e in elements]
        self.len = sum(map(len, self.elements))

    def format(
        self, tabsize=4, offset=0, line_offset=0, max_col=80, compact=False
    ):
        s = ""
        for e in self.elements:
            value, offset = e.format(
                tabsize=tabsize,
                offset=offset,
                line_offset=line_offset,
                max_col=max_col,
                compact=compact,
            )
            s += value
        return s, offset


class Text(TerminalPrinter):
    def __init__(self, value, color=None):
        self.value = value
        self.color = color
        self.len = len(self.value)

    def format(
        self, tabsize=4, offset=0, line_offset=0, max_col=80, compact=False
    ):
        return self.value, offset + len(self)


@ovld
def standard_terminal(self, node: Tag):
    """Generate a terminal representation."""
    return Breakable(
        start=f"<{node.name}>",
        body=[self(child) for child in node.children],
        end=f"</{node.name}>",
    )


@ovld
def standard_terminal(self, node: type(H.atom)):
    (child,) = node.children
    return Text(self(child))


@ovld
def standard_terminal(self, node: type(H.symbol)):
    (child,) = node.children
    return Text(self(child))


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
        start=start,
        body=join(map(self, node.children), delim),
        end=end,
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
