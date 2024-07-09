def join(seq, sep):
    seq = list(seq)
    if not seq:
        return []
    else:
        *first, last = seq
        return [Sequence(x, sep) for x in first] + [last]


class TextFormatter:
    def __str__(self):  # pragma: no cover
        raise Exception("Override this")

    def to_string(self):
        return str(self)

    def empty(self):  # pragma: no cover
        return False


class Breakable(TextFormatter):
    __slots__ = ("start", "body", "end")

    def __init__(self, start, body, end):
        self.start = start
        self.body = body
        self.end = end

    def __str__(self):
        start = str(self.start) if self.start is not None else ""
        body = "".join(map(str, self.body))
        end = str(self.end) if self.end is not None else ""
        return f"{start}{body}{end}"

    def empty(self):
        return not (self.start or self.end or self.body)


class Sequence(TextFormatter):
    __slots__ = ("elements",)

    def __init__(self, *elements):
        self.elements = elements

    def __str__(self):
        return "".join(map(str, self.elements))

    def empty(self):
        return not self.elements


class Text(TextFormatter):
    __slots__ = ("value",)

    def __init__(self, value):
        self.value = value

    def __str__(self):
        return self.value

    def empty(self):
        return not self.value
