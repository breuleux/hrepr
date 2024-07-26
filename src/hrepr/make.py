from .h import H

ABSENT = object()


class StandardMaker:
    def __init__(self, hrepr):
        self.hrepr = hrepr
        self.H = self.hrepr.H

    def tag_type(self, node, t):
        if t is None:
            return node
        if not isinstance(t, str):
            t = t.__name__
        return node[f"hreprt-{t}"]

    def ref(self, num, loop=False, content=None):
        sym = "⟳" if loop else "#"
        ref = self.H.span["hrepr-ref"](sym, num)
        if content:
            return self.H.div["hrepr-refbox"](ref("="), content)
        else:
            return ref

    def defn(self, key, name, type=None):
        node = H.span[f"hreprk-{key}"](
            H.span["hrepr-defn-key"](key),
            " ",
            H.span["hrepr-defn-name"](name),
        )
        return self.tag_type(node, type)

    def atom(self, *content, type=None, value=ABSENT):
        rval = self.tag_type(H.span(*content), type)
        if value is not ABSENT:
            rval = rval[f"hreprv-{value}"]
        return rval

    def sequence(
        self,
        seq,
        transform=None,
        sequence_max=None,
        rows=False,
        ellipsis=None,
        ntrail=2,
    ):
        def adjusted_transform(x):
            if rows:
                return [transform(y) for y in x]
            else:
                return transform(x)

        ellipsis = ellipsis or self.H.span("...")["hrepr-ellipsis"]

        cap = (
            self.hrepr.config.sequence_max
            if sequence_max is None
            else sequence_max
        )
        if transform is None:
            transform = self.hrepr

        if not cap or cap < ntrail or len(seq) <= cap:
            return [adjusted_transform(x) for x in seq]
        else:
            seq = list(seq)
            before = [adjusted_transform(x) for x in seq[: cap - ntrail]]
            after = (
                [adjusted_transform(x) for x in seq[-ntrail:]] if ntrail else []
            )
            return [*before, ellipsis, *after]

    def flow(self, seq, **kwargs):
        return H.div["hreprl-h", "hrepr-body"](
            [H.div(x) for x in self.sequence(seq, **kwargs)]
        )

    def short(self, x):
        return H.div["hreprl-s", "hrepr-body"](H.div(x))

    def table(self, rows, **kwargs):
        t = H.table["hrepr-body"]()
        width = 3
        for row in self.sequence(rows, rows=True, **kwargs):
            if isinstance(row, (list, tuple)):
                width = len(row)
                t = t(H.tr([H.td(x) for x in row]))
            else:
                t = t(H.tr(H.td(row, colspan=width)))
        return t

    def bracketed(self, body, start, end, type=None):
        node = H.div(
            H.div["hrepr-open"](start),
            body,
            H.div["hrepr-close"](end),
        )
        return self.tag_type(node, type)["hrepr-bracketed"]

    def title_box(self, title, body, type=None, layout="v", wrap_body=True):
        if wrap_body:
            body = H.div["hrepr-body", f"hreprl-{layout}"](body)
        node = H.div["hrepr-instance", f"hreprl-{layout}"](
            H.div["hrepr-title"](title), body
        )
        return self.tag_type(node, type)

    def instance(self, title, fields, delimiter=None, type=None):
        if isinstance(delimiter, str):
            delimiter = H.span["hrepr-delim"](delimiter)
        body = self.table(
            [[self.atom(k, type="symbol"), delimiter, v] for k, v in fields]
        )
        return self.title_box(
            title, body, type=type, layout="v", wrap_body=False
        )
