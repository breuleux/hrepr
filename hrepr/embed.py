import json
from itertools import count
from typing import Union

from ovld import ovld

from .h import H, Tag
from .j import Code, Into, J, Module, Script
from .resource import JSExpression, Resource
from .textgen_simple import Breakable, Sequence, Text, join

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
def js_embed(self, t: Tag):
    innerhtml = str(t)
    return f"$$HREPR.fromHTML({self(innerhtml)})"


_c = count()


def gensym(symbol):
    return f"{symbol}__{next(_c)}"


@ovld
def js_embed(self, j: J):
    resources = []
    if j.stylesheet is not None:
        styles = (
            j.stylesheet
            if isinstance(j.stylesheet, Sequence)
            else [j.stylesheet]
        )
        resources.extend(
            [
                src
                if isinstance(src, Tag)
                else H.link(rel="stylesheet", href=src)
                for src in styles
            ]
        )
    if j.namespace is not None:
        varname = gensym(j.symbol or "default")
        resources.append(
            Module(module=j.namespace, varname=varname, namespace=True)
        )
    elif j.module is not None:
        varname = gensym(j.symbol or "default")
        resources.append(
            Module(
                module=j.module,
                symbol=j.symbol,
                varname=varname,
                namespace=False,
            )
        )
    elif j.src is not None:
        varname = j.symbol
        resources.append(Script(src=j.src, symbol=j.symbol))
    elif j.code is not None:
        varname = j.symbol
        resources.append(Code(code=j.code, symbol=j.symbol))
    else:
        varname = "window"

    result = varname
    prev_result = varname
    last_symbol = None

    for entry in j.path:
        if varname is None:
            assert isinstance(entry, str)
            result = prev_result = varname = entry
            continue
        if isinstance(entry, str):
            prev_result = result
            last_symbol = entry
            result = Sequence(result, ".", entry)
        elif isinstance(entry, (list, tuple)):
            result = Breakable(
                start="$$HREPR.ucall(",
                body=join(
                    [prev_result, self(last_symbol), *[self(x) for x in entry]],
                    sep=",",
                ),
                end=")",
            )
        else:  # pragma: no cover
            raise TypeError()

    if resources:
        result = Sequence(result, resources=resources)
    return result


@ovld
def js_embed(self, i: Into):
    return Text("$$INTO", resources=[i])


@ovld
def js_embed(self, res: Resource):
    return self(res.obj)


@ovld
def js_embed(self, x: object):
    raise TypeError(
        f"Resources of type {type(x).__name__} cannot be serialized to JavaScript."
    )
