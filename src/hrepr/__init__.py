"""Extensible HTML representation for Python objects."""

from . import elements, h
from .core import Config, Hrepr, HreprState, Interface, StdHrepr
from .h import HTML, H, HType, Tag
from .hgen import BlockGenerator, HTMLGenerator, standard_html
from .j import J, Returns
from .resource import JSExpression, Resource

returns = Returns
h.standard_html = standard_html

config_defaults = {
    "string_cutoff": 20,
    "bytes_cutoff": 20,
    "sequence_max": 100,
}

hrepr = Interface(StdHrepr, **config_defaults)

__all__ = [
    "BlockGenerator",
    "Config",
    "H",
    "HTML",
    "HTMLGenerator",
    "HType",
    "Hrepr",
    "HreprState",
    "Interface",
    "J",
    "JSExpression",
    "Resource",
    "Returns",
    "StdHrepr",
    "Tag",
    "elements",
    "h",
    "hrepr",
    "returns",
    "standard_html",
]
