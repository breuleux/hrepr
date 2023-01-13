import json
from typing import Union

from ovld import ovld

from .h import HType, Tag
from .resource import JSExpression, Resource
from .textgen import Breakable, Sequence, Text, join

_type = type


##################################
# Embedding data in an attribute #
##################################


@ovld
def attr_embed(self, attr: str, value: bool):
    if value is False:
        return None
    elif value is True:
        return value


@ovld
def attr_embed(self, attr: str, value: Union[str, int, float]):
    return str(value)


@ovld
def attr_embed(self, attr: str, value: Union[list, tuple, set, frozenset]):
    return " ".join(self(attr, cls) for cls in value)


@ovld
def attr_embed(self, attr: str, expr: JSExpression):
    return expr


@ovld
def attr_embed(self, attr: str, t: Tag):
    tag_id = t.get_attribute("id", None)
    if not tag_id:
        raise ValueError(f"Cannot embed <{t.name}> element without an id.")
    return f"#{tag_id}"


@ovld
def attr_embed(self, attr: str, value: object):
    raise TypeError(
        f"Resources of type {type(value).__name__} cannot be serialized as an attribute."
    )


################################
# Embedding data in JavaScript #
################################


@ovld
def js_embed(self, d: dict):
    return Breakable(
        start="{",
        body=join(
            [Sequence(self(k), ": ", self(v)) for k, v in d.items()], sep=", "
        ),
        end="}",
    )


@ovld
def js_embed(self, seq: Union[list, tuple]):
    return Breakable(
        start="[",
        body=join(map(self, seq), sep=", "),
        end="]",
    )


@ovld
def js_embed(self, x: Union[int, float, str, bool, _type(None)]):
    return Text(json.dumps(x))


@ovld
def js_embed(self, expr: JSExpression):
    return expr.code


@ovld
def js_embed(self, t: HType.self):
    return "self"


@ovld
def js_embed(self, t: Tag):
    tag_id = t.get_attribute("id", None)
    if not tag_id:
        raise ValueError(f"Cannot embed <{t.name}> element without an id.")
    return f"document.getElementById('{tag_id}')"


@ovld
def js_embed(self, res: Resource):
    return self(res.obj)


@ovld
def js_embed(self, x: object):
    raise TypeError(
        f"Resources of type {type(x).__name__} cannot be serialized to JavaScript."
    )
