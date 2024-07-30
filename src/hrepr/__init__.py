"""Extensible HTML representation for Python objects."""

from . import elements, h
from .core import Config, Hrepr, HreprState, Interface, StdHrepr  # noqa: F401
from .h import HTML, H, HType, Tag  # noqa: F401
from .hgen import BlockGenerator, HTMLGenerator, standard_html
from .j import J, Returns  # noqa: F401

returns = Returns
h.standard_html = standard_html

config_defaults = {
    "string_cutoff": 20,
    "bytes_cutoff": 20,
    "sequence_max": 100,
}

hrepr = Interface(StdHrepr, **config_defaults)
