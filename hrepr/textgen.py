import math
from dataclasses import dataclass
from dataclasses import replace as dc_replace


@dataclass
class Context:
    tabsize: int
    max_col: int
    offset: int
    line_offset: int
    max_indent: int = None
    overflow: str = "allow"

    replace = dc_replace

    def __post_init__(self):
        if self.max_col is None:
            self.max_col = math.inf

    def next_line_offset(self):
        max_indent = (
            max(self.max_col - 15, 0)
            if (self.max_indent is None and self.overflow != "allow")
            else (self.max_indent or 1e32)
        )
        return min(self.line_offset + self.tabsize, max_indent)

    def indent(self):
        return " " * self.line_offset

    def format(self, x, **modifs):
        result, offset = x.format(self.replace(**modifs))
        if self.overflow != "allow":
            linepfx = r"\ " if self.overflow == "backslash" else ""
            while True:
                diff = self.max_col - offset
                if diff >= 0:
                    break
                overflow = result[diff:]
                if not overflow.strip():
                    result = result[:diff]
                    break
                else:
                    result = (
                        f"{result[:diff]}\n{self.indent()}{linepfx}{overflow}"
                    )
                offset = self.line_offset + len(overflow) + len(linepfx)

        return result, offset


def ensure_text(x):
    if isinstance(x, str):
        return Text(x)
    else:
        return x


def join(seq, sep):
    seq = list(seq)
    if not seq:
        return []
    else:
        *first, last = seq
        return [Sequence(x, sep) for x in first] + [last]


class TextFormatter:
    def to_string(self, **config):
        value, offset = self.format(
            Context(
                tabsize=4,
                max_col=None,
                offset=0,
                line_offset=0,
                max_indent=None,
            ).replace(**config),
        )
        return value

    def __len__(self):
        return self.len

    def __str__(self):  # pragma: no cover
        return self.to_string()


class Breakable(TextFormatter):
    def __init__(self, start, body, end):
        self.start = ensure_text(start)
        self.body = list(map(ensure_text, body))
        self.end = ensure_text(end)
        self.len = (
            len(self.start or "")
            + sum(map(len, self.body))
            + len(self.end or "")
        )

    def format(self, ctx):
        s = ""

        if self.start is not None:
            value, offset = ctx.format(self.start)
            s += value
        else:
            offset = ctx.offset

        if offset + len(self) - len(self.start or "") <= ctx.max_col:
            for x in self.body:
                value, offset = ctx.format(x, offset=offset)
                s += value

            if self.end is not None:
                value, offset = ctx.format(self.end, offset=offset)
                s += value
            return s, offset
        else:
            ind = ctx.next_line_offset()
            inner_ctx = ctx.replace(offset=ind, line_offset=ind)
            for x in self.body:
                value, offset = inner_ctx.format(x)
                s += "\n" + inner_ctx.indent() + value

            if self.end is not None:
                value, offset = ctx.format(self.end, offset=ctx.line_offset)
                s += "\n" + ctx.indent() + value

            return s, offset


class Sequence(TextFormatter):
    def __init__(self, *elements):
        self.elements = [Text(e) if isinstance(e, str) else e for e in elements]
        self.len = sum(map(len, self.elements))

    def format(self, ctx):
        s = ""
        offset = ctx.offset
        for e in self.elements:
            value, offset = ctx.format(e, offset=offset)
            s += value
        return s, offset


class Text(TextFormatter):
    def __init__(self, value):
        self.value = value
        self.len = len(self.value)

    def format(self, ctx):
        return self.value, ctx.offset + len(self)
