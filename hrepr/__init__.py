"""Extensible HTML representation for Python objects."""

from .core import Config, Hrepr, HreprState, Interface, StdHrepr
from .h import HTML, H, Tag, css_hrepr
from .std import standard_html
from .term import standard_terminal

hrepr = Interface(StdHrepr, backend=standard_html)
trepr = Interface(StdHrepr, backend=standard_terminal)


def pprint(x, **config):  # pragma: no cover
    print(pstr(**config))


def pstr(x, indent=4, max_col=80, max_indent=None, overflow="allow", **config):
    return trepr(x, **config).to_string(
        tabsize=indent,
        max_col=max_col,
        max_indent=max_indent,
        overflow=overflow,
    )
