import math
import types
from collections import Counter
from dataclasses import fields as dataclass_fields
from dataclasses import is_dataclass
from pathlib import Path
from typing import Union

from ovld import OvldMC, extend_super, ovld

from .h import H, Tag
from .j import J
from .make import StandardMaker

ABSENT = object()

_type = type
here = Path(__file__).parent
styledir = here / "style"


class Config:
    def __init__(self, cfg={}, parent=None):
        self._parent = parent
        self.__dict__.update(cfg)

    def with_config(self, cfg):
        return Config(cfg, self)

    def __getattr__(self, attr):
        # Only triggers for attributes not in __dict__
        if self._parent:
            return getattr(self._parent, attr)
        return None


class HreprState:
    def __init__(self):
        self.types_seen = set()
        self.stack = Counter()
        self.registry = {}
        self.depth = -1
        self.refs = {}

    def get_ref(self, objid):
        return self.refs.setdefault(objid, len(self.refs) + 1)

    def registered(self, objid):
        return objid in self.registry

    def register(self, objid, value):
        self.registry.setdefault(objid, value)

    def reregister(self, objid, value):
        if objid in self.registry:
            self.registry[objid] = value

    def make_refmap(self):
        rval = {}
        for objid, label in self.refs.items():
            rval[id(self.registry[objid])] = label
        return rval


class Hrepr(metaclass=OvldMC):
    @classmethod
    def make_interface(cls, **kw):
        return Interface(cls, **kw)

    def __init__(
        self,
        *,
        H=H,
        maker=StandardMaker,
        config=None,
        master=None,
        preprocess=None,
        postprocess=None,
    ):
        self.H = H
        self.config = config or Config()
        self.master = master or self
        self.state = master.state if master else HreprState()
        self.preprocess = preprocess
        self.postprocess = postprocess
        self.make = maker(self)

    def with_config(self, config):
        if not config:
            return self
        else:
            cfg = self.config.with_config(config)
            return type(self)(
                H=self.H,
                config=cfg,
                master=self.master,
                preprocess=self.preprocess,
                postprocess=self.postprocess,
            )

    def ref(self, obj, loop=False):
        num = self.state.get_ref(id(obj))
        if self.config.shortrefs:
            return self.make.ref(loop=loop, num=num)
        else:
            return self.make.ref(
                loop=loop, num=num, content=self.hrepr_short(obj)
            )

    def global_resources(self):  # pragma: no cover
        return ()

    @ovld
    def hrepr_resources(self, cls: object):
        if hasattr(cls, "__hrepr_resources__"):
            return cls.__hrepr_resources__(self.H)
        else:
            return []

    @ovld.dispatch
    def hrepr(ovldcall, obj):
        self = ovldcall.obj
        rval = ovldcall.resolve(obj)(obj)
        if rval is NotImplemented:
            return self.hrepr_short(obj)
        else:
            self.state.register(id(obj), rval)
            return rval

    def hrepr(self, obj: object):
        if hasattr(obj, "__hrepr__"):
            return obj.__hrepr__(self.H, self)
        elif is_dataclass(type(obj)):
            return self.make.instance(
                title=type(obj).__name__,
                fields=[
                    [field.name, getattr(obj, field.name)]
                    for field in dataclass_fields(obj)
                ],
                delimiter="=",
                type=type(obj),
            )
        else:
            return NotImplemented

    @ovld
    def hrepr_short(self, obj: object):
        if hasattr(obj, "__hrepr_short__"):
            return obj.__hrepr_short__(self.H, self)
        elif is_dataclass(type(obj)):
            return self.make.title_box(
                title=type(obj).__name__, body="...", type=type(obj), layout="s"
            )

        def _xtn(x):
            tx = type(x)
            mn = tx.__module__
            if mn == "builtins":
                return tx.__qualname__
            else:
                return f"{mn}.{tx.__qualname__}"

        rval = self.make.atom("<", _xtn(obj), ">", type=type(obj))
        self.state.register(id(obj), rval)
        return rval

    def __call__(self, obj, **config):
        if self.preprocess is not None:
            obj = self.preprocess(obj, self)

        self.state.skip_default = False
        runner = self.with_config(config)
        ido = id(obj)
        if self.state.stack[ido]:
            return runner.ref(obj, loop=True)

        if (
            not isinstance(obj, Tag)
            and self.state.registered(ido)
            and not runner.config.norefs
        ):
            return runner.ref(obj)

        # Push object on the stack to detect circular references
        self.state.stack[ido] += 1
        self.state.depth += 1

        if (
            runner.config.max_depth is not None
            and self.state.depth >= runner.config.max_depth
        ):
            rval = runner.hrepr_short(obj)
        else:
            rval = runner.hrepr(obj)

        if self.postprocess is not None:
            rval = self.postprocess(rval, obj, self)
            self.state.reregister(id(obj), rval)

        # Check that it's the right type
        htype = self.H._tag_class
        if isinstance(rval, J):
            rval = rval.as_node()
        if not isinstance(rval, htype):
            raise TypeError(
                f"Return value of hrepr({type(obj)}) must be an "
                f"instance of {htype}, not {type(rval)}."
            )

        # Pop object from the stack
        self.state.depth -= 1
        self.state.stack[ido] -= 1

        # Collect resources for this object
        cls = type(obj)
        resources = self.hrepr_resources[cls](cls)
        rval = rval.fill(resources=resources)
        self.state.reregister(id(obj), rval)

        return rval


_remap = {}
for i in range(0x20):
    c = chr(i)
    _remap[c] = f"\\x{c.encode().hex()}"
_remap.update({"\\": "\\\\", "\r": "\\r", "\n": "\\n", "\t": "\\t"})


def _encode(s):
    return "".join(_remap.get(c, c) for c in s)


class StdHrepr(Hrepr):
    def global_resources(self):
        return (self.H.style((styledir / "hrepr.css").read_text()),)

    # Lists

    @extend_super
    def hrepr(self, xs: list):
        return self.make.bracketed(
            self.make.flow(xs), start="[", end="]", type=type(xs)
        )

    @extend_super
    def hrepr_short(self, xs: list):
        return self.make.bracketed(
            self.make.short("..."), start="[", end="]", type=type(xs)
        )

    # Tuples

    def hrepr(self, xs: tuple):
        return self.make.bracketed(
            self.make.flow(xs), start="(", end=")", type=type(xs)
        )

    def hrepr_short(self, xs: tuple):
        return self.make.bracketed(
            self.make.short("..."), start="(", end=")", type=type(xs)
        )

    # Sets

    def hrepr(self, xs: Union[set, frozenset]):
        return self.make.bracketed(
            self.make.flow(xs), start="{", end="}", type=type(xs)
        )

    def hrepr_short(self, xs: Union[set, frozenset]):
        return self.make.bracketed(
            self.make.short("..."), start="{", end="}", type=type(xs)
        )

    # Dictionaries

    def hrepr(self, obj: dict):
        return self.make.bracketed(
            self.make.table(
                [[k, H.span["hrepr-delim"](": "), v] for k, v in obj.items()]
            ),
            start="{",
            end="}",
            type=type(obj),
        )

    def hrepr_short(self, xs: dict):
        return self.make.bracketed(
            self.make.short("..."), start="{", end="}", type=type(xs)
        )

    # Other structures

    def hrepr(self, dk: _type({}.keys())):
        return self.make.bracketed(
            self.make.flow(dk), start="dict_keys(", end=")", type=type(dk)
        )

    def hrepr_short(self, dk: _type({}.keys())):
        return self.make.bracketed(
            self.make.short("..."), start="dict_keys(", end=")", type=type(dk)
        )

    def hrepr(self, dv: _type({}.values())):
        return self.make.bracketed(
            self.make.flow(dv), start="dict_values(", end=")", type=type(dv)
        )

    def hrepr_short(self, dv: _type({}.values())):
        return self.make.bracketed(
            self.make.short("..."), start="dict_values(", end=")", type=type(dv)
        )

    # Exceptions

    def hrepr(self, obj: Exception):
        return self.make.title_box(
            title=type(obj).__name__,
            body=[
                self.H.span(str(obj.args[0])) if obj.args else "",
                *self.make.sequence(obj.args[1:]),
            ],
            type=type(obj),
            layout="h",
        )["hrepr-error"]

    # Functions and methods

    def hrepr_short(self, obj: types.FunctionType):
        # types.LambdaType is types.FunctionType
        return self.make.defn("function", obj.__name__)

    def hrepr_short(self, obj: types.CoroutineType):
        return self.make.defn("coroutine", obj.__name__)

    def hrepr_short(self, obj: types.GeneratorType):
        return self.make.defn("generator", obj.__name__)

    def hrepr_short(self, obj: types.AsyncGeneratorType):
        return self.make.defn("async_generator", obj.__name__)

    def hrepr_short(self, obj: Union[types.MethodType, _type([].__str__)]):
        # Second one is types.MethodWrapperType but it's not exposed
        # in the types module in 3.6
        slf = obj.__self__
        slf = getattr(slf, "__name__", f"<{type(slf).__name__}>")
        return self.make.defn("method", f"{slf}.{obj.__name__}")

    def hrepr_short(
        self, obj: Union[_type(object.__str__), _type(dict.update)]
    ):
        # These are types.WrapperDescriptorType and types.MethodDescriptorType
        # but they are not exposed in the types module in 3.6
        objc = obj.__objclass__.__name__
        return self.make.defn("descriptor", f"{objc}.{obj.__name__}")

    def hrepr_short(self, obj: types.BuiltinMethodType):
        # types.BuiltinFunctionType is types.BuiltinMethodType
        slf = obj.__self__
        slf = getattr(slf, "__name__", f"<{type(slf).__name__}>")
        if slf == "builtins":
            # Let's not be redundant
            return self.make.defn("builtin", obj.__name__)
        else:
            return self.make.defn("builtin", f"{slf}.{obj.__name__}")

    def hrepr_short(self, obj: type):
        key = "metaclass" if issubclass(obj, type) else "class"
        return self.make.defn(key, obj.__name__)

    def hrepr_short(self, obj: types.ModuleType):
        return self.make.defn("module", obj.__name__)

    # Strings

    def hrepr(self, x: str):
        cutoff = self.config.string_cutoff or math.inf
        if len(x) <= cutoff:
            # This will fall back to hrepr_short, which will not display #ref=
            # for multiple instances of the same string.
            return NotImplemented
        else:
            return self.make.atom(_encode(x), type="str")

    def hrepr_short(self, x: str):
        cutoff = self.config.string_cutoff or math.inf
        if len(x) > cutoff:
            x = x[: cutoff - 3] + "..."
        return self.make.atom(_encode(x), type="str")

    # Bytes

    def hrepr(self, x: bytes):
        cutoff = self.config.bytes_cutoff or math.inf
        if len(x) <= cutoff:
            return NotImplemented
        else:
            return self.make.atom(x.hex(), type="bytes")

    def hrepr_short(self, x: bytes):
        cutoff = self.config.bytes_cutoff or math.inf
        hx = x.hex()
        if len(hx) > cutoff:
            hx = hx[: cutoff - 3] + "..."
        return self.make.atom(hx, type="bytes")

    # Numbers

    def hrepr_short(self, x: Union[int, float]):
        return self.make.atom(str(x), type=type(x))

    # Booleans

    def hrepr_short(self, x: bool):
        return self.make.atom(str(x), value=x)

    # None

    def hrepr_short(self, x: _type(None)):
        return self.make.atom(str(x), value=x)

    # Tags

    def hrepr(self, x: Tag):
        return x

    def hrepr_short(self, x: Tag):
        return x

    # JavaScript

    def hrepr(self, x: J):
        return H.inline(x)

    def hrepr_short(self, x: J):
        return H.inline(x)


def inject_reference_numbers(hcall, node, refmap):
    if isinstance(node, Tag):
        new_children = tuple(
            inject_reference_numbers(hcall, child, refmap)
            for child in node.children
        )
        if any(change for change, _ in new_children):
            new_node = type(node)(
                name=node.name,
                attributes=node.attributes,
                children=tuple(child for _, child in new_children),
                resources=node.resources,
            )
        else:
            new_node = node

        refnum = refmap.get(id(node), None)
        if refnum is not None:
            return True, hcall.make.ref(content=node, num=refnum)
        else:
            return True, new_node
    else:
        return False, node


def _mix(hclass, mixins):
    if mixins:
        if isinstance(mixins, type):
            mixins = [mixins]
        hclass = hclass.create_subclass(*mixins)
    return hclass


class Interface:
    def __init__(
        self,
        hclass,
        *,
        mixins=None,
        preprocess=ABSENT,
        postprocess=ABSENT,
        inject_references=True,
        fill_resources=True,
        **config_defaults,
    ):
        self.hrepr_options = {}
        self.config_defaults = {}
        self.configure(
            hclass=hclass,
            mixins=mixins,
            preprocess=preprocess,
            postprocess=postprocess,
            inject_references=inject_references,
            fill_resources=fill_resources,
            **config_defaults,
        )

    def copy(self):
        return type(self)(
            hclass=self.hclass,
            inject_references=self.inject_references,
            fill_resources=self.fill_resources,
            **self.hrepr_options,
            **self.config_defaults,
        )

    def variant(self, **options):
        return self.copy().configure(**options)

    def configure(
        self,
        *,
        hclass=None,
        mixins=None,
        preprocess=ABSENT,
        postprocess=ABSENT,
        inject_references=ABSENT,
        fill_resources=ABSENT,
        **config_defaults,
    ):
        if hclass is not None:
            self.hclass = hclass
        self.hclass = _mix(self.hclass, mixins)
        if preprocess is not ABSENT:
            self.hrepr_options["preprocess"] = preprocess
        if postprocess is not ABSENT:
            self.hrepr_options["postprocess"] = postprocess
        if inject_references is not ABSENT:
            self.inject_references = inject_references
        if fill_resources is not ABSENT:
            self.fill_resources = fill_resources
        self.config_defaults.update(config_defaults)
        return self

    def page(self, *objs, file=None, **config):
        result = self(*objs, **config).as_page()
        if file is None:
            return result
        elif isinstance(file, str):  # pragma: no cover
            with open(file, "w") as f:
                f.write(str(result) + "\n")
        else:  # pragma: no cover
            file.write(str(result) + "\n")

    def __call__(self, *objs, **config):
        if config:
            return self.variant(**config)(*objs)
        else:
            hcall = self.hclass(
                H=H, config=Config(self.config_defaults), **self.hrepr_options
            )
            if len(objs) == 1:
                rval = hcall(objs[0])
            else:
                rval = H.inline(*map(hcall, objs))
            if self.inject_references:
                _, rval = inject_reference_numbers(
                    hcall, rval, hcall.state.make_refmap()
                )
            if self.fill_resources:
                rval = rval.fill(resources=hcall.global_resources())
            return rval
