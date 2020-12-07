"""Extended JSON generator.

This generator is meant to generate structures to embed into JavaScript code,
so it may generate invalid JSON (which is why we cannot use the json package).

In particular, interactive backends may generate something special for
functions, so that JS code can call Python functionality. By default, hjson
returns null as the representation of functions.
"""

import json
from types import FunctionType, MethodType

from ovld import ovld

from .textgen import Breakable, Sequence, Text, join


@ovld
def dump(self, d: dict):
    return Breakable(
        start="{",
        body=join(
            [Sequence(self(k), ": ", self(v)) for k, v in d.items()], sep=", "
        ),
        end="}",
    )


@ovld
def dump(self, seq: (list, tuple)):
    return Breakable(start="[", body=join(map(self, seq), sep=", "), end="]",)


@ovld
def dump(self, x: (int, float, str, bool, type(None))):
    return Text(json.dumps(x))


@ovld
def dump(self, fn: (FunctionType, MethodType)):
    return self(None)


@ovld
def dump(self, d: object):
    raise TypeError(
        f"Objects of type {type(d).__name__} cannot be JSON-serialized."
    )


def dumps(obj, **fmt):
    return dump(obj).to_string(**fmt)
