"""Extended JSON generator.

This generator is meant to generate structures to embed into JavaScript code,
so it may generate invalid JSON (which is why we cannot use the json package).

In particular, interactive backends may generate something special for
functions, so that JS code can call Python functionality. By default, hjson
returns null as the representation of functions.
"""

import json
from types import FunctionType, MethodType
from typing import Union

from ovld import ovld

from .h import HType, Tag
from .resource import Resource
from .textgen import Breakable, Sequence, Text, join

_type = type


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
def dump(self, seq: Union[list, tuple]):
    return Breakable(start="[", body=join(map(self, seq), sep=", "), end="]",)


@ovld
def dump(self, x: Union[int, float, str, bool, _type(None)]):
    return Text(json.dumps(x))


@ovld
def dump(self, fn: Union[FunctionType, MethodType]):
    return self(None)


@ovld
def dump(self, t: HType.self):
    return f"self"


@ovld
def dump(self, t: Tag):
    tag_id = t.get_attribute("id")
    if not tag_id:
        raise ValueError(f"Cannot embed <{t.name}> element without an id.")
    return f"document.getElementById('{tag_id}')"


@ovld
def dump(self, res: Resource):
    raise TypeError(
        f"Resources of type {type(res.obj).__name__} cannot be serialized to JavaScript."
    )


@ovld
def dump(self, x: object):
    return self(Resource(x))
