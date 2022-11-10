"""Extensible HTML representation for Python objects."""

from .core import Config, Hrepr, HreprState, Interface, StdHrepr  # noqa: F401
from .h import HTML, H, HType, Tag  # noqa: F401
from .std import standard_html

config_defaults = {
    "string_cutoff": 20,
    "bytes_cutoff": 20,
    "sequence_max": 100,
}

hrepr = Interface(StdHrepr, backend=standard_html, **config_defaults)
