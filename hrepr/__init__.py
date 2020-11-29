"""Extensible HTML representation for Python objects."""

from .core import Config, Hrepr, HreprState, Interface, StdHrepr  # noqa: F401
from .h import HTML, H, Tag, css_hrepr  # noqa: F401
from .std import standard_html
from .term import standard_terminal

hrepr = Interface(StdHrepr, backend=standard_html)
trepr = Interface(StdHrepr, backend=standard_terminal)


def pprint(x, **config):  # pragma: no cover
    """Pretty-print an object.

    Arguments:
        indent: The number of spaces to use for indented blocks.
        max_col: The maximum width for the generated text.
        max_indent: The maximum indent (defaults to max_col - 15 if overflow
            is "allow").
        overflow: How to handle non-breakable text.
            * "allow" to let non-breakable text exceed max_col.
            * "break" to break the text on multiple indented lines.
            * "backslash" to break the text on multiple indented lines, with
                a leading backslash on each overflow line.
        config: Configuration settings (dependent on the pretty-printer for
            each object).
    """
    print(pstr(x, **config))


def pstr(x, indent=4, max_col=80, max_indent=None, overflow="allow", **config):
    """Convert x to a pretty-printed string.

    Arguments:
        indent: The number of spaces to use for indented blocks.
        max_col: The maximum width for the generated text.
        max_indent: The maximum indent (defaults to max_col - 15 if overflow
            is "allow").
        overflow: How to handle non-breakable text.
            * "allow" to let non-breakable text exceed max_col.
            * "break" to break the text on multiple indented lines.
            * "backslash" to break the text on multiple indented lines, with
                a leading backslash on each overflow line.
        config: Configuration settings (dependent on the pretty-printer for
            each object).
    """
    return trepr(x, **config).to_string(
        tabsize=indent,
        max_col=max_col,
        max_indent=max_indent,
        overflow=overflow,
    )
