import re
from itertools import count
from uuid import uuid4

from ovld import OvldMC

embed_key = uuid4().hex


class Registry:
    def __init__(self):
        self.reset()

    def register(self, resource):
        currid = next(self.id)
        self.id_to_resource[currid] = resource
        return currid

    def resolve(self, id):
        return self.id_to_resource[id]

    def reset(self):
        self.id = count()
        self.id_to_resource = {}


registry = Registry()


class Resource:
    def __init__(self, obj, variant=""):
        self.obj = obj
        self.variant = variant
        self.id = registry.register(self)

    def __str__(self):
        return f"[{embed_key}:{self.variant}{self.id}]"


class JSExpression:
    def __init__(self, code):
        self.code = code


class JSFunction(JSExpression):
    def __init__(self, argnames, code, expression=None):
        if expression is None:
            expression = ";" not in code
        if not isinstance(argnames, (list, tuple)):
            argnames = (argnames,)
        argstring = "({})".format([", ".join(argnames)])
        if expression:
            complete_code = f"{argstring} => {code}"
        else:
            complete_code = f"{argstring} => {{ {code} }}"
        super().__init__(code=complete_code)


class Embedder(metaclass=OvldMC):
    def __init__(self, registry):
        self.registry = registry

    def embed(self, obj, resource, tag, attr):
        if tag.name == "script" and attr is None:
            return "undefined"
        else:
            return "CANNOT_EMBED"

    def __call__(self, tag, attr, value):
        def sub(m):
            res = self.registry.resolve(int(m.groups()[0]))
            return self.embed(res.obj, res, tag, attr)

        return re.sub(
            pattern=rf"\[{embed_key}:([0-9]+)\]", string=value, repl=sub
        )
