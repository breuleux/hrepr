import types
from collections import Counter
from dataclasses import fields as dataclass_fields
from dataclasses import is_dataclass

from ovld import OvldMC, has_attribute, meta, ovld

from . import std
from .h import H, Tag, css_hrepr
from .std import standard_html

default_string_cutoff = 20
default_bytes_cutoff = 20


ABSENT = object()


def _tn(x):
    return type(x).__name__


def _xtn(x):
    tx = type(x)
    mn = tx.__module__
    if mn == "builtins":
        return tx.__qualname__
    else:
        return f"{mn}.{tx.__qualname__}"


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
        kw = {"backend": standard_html, **kw}
        return Interface(cls, **kw)

    def __init__(
        self,
        *,
        H=H,
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
        ref = self.H.ref(loop=loop, num=num)
        if not self.config.shortrefs:
            ref = ref(self.hrepr_short(obj))
        return ref

    def global_resources(self):  # pragma: no cover
        return ()

    @ovld
    def hrepr_resources(self, cls: object):
        return []

    def hrepr_resources(self, cls: has_attribute("__hrepr_resources__")):
        return cls.__hrepr_resources__(self.H)

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
        return NotImplemented

    def hrepr(self, obj: has_attribute("__hrepr__")):
        return obj.__hrepr__(self.H, self)

    @ovld
    def hrepr_short(self, obj: object):
        clsn = _tn(obj)
        rval = self.H.atom("<", _xtn(obj), ">", type=clsn)
        self.state.register(id(obj), rval)
        return rval

    @ovld
    def hrepr_short(self, obj: has_attribute("__hrepr_short__")):
        return obj.__hrepr_short__(self.H, self)

    def __call__(self, obj, **config):
        if self.preprocess is not None:
            obj = self.preprocess(obj, self)

        self.state.skip_default = False
        runner = self.with_config(config)
        ido = id(obj)
        if self.state.stack[ido]:
            return runner.ref(obj, loop=True)

        if self.state.registered(ido) and not runner.config.norefs:
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
        htype = self.H.tag_class
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
_remap.update(
    {"\\": "\\\\", "\r": "\\r", "\n": "\\n", "\t": "\\t"}
)


def _encode(s):
    return "".join(_remap.get(c, c) for c in s)


class StdHrepr(Hrepr):
    def __init__(self, *, std=std, **kw):
        super().__init__(**kw)
        self.std = std

    def global_resources(self):
        return (self.H.style(css_hrepr),)

    # Lists

    def hrepr(self, xs: list):
        return self.H.bracketed(
            *[self(x) for x in xs], start="[", end="]", type=_tn(xs),
        )

    def hrepr_short(self, xs: list):
        return self.H.bracketed(
            "...", short=True, start="[", end="]", type=_tn(xs),
        )

    # Tuples

    def hrepr(self, xs: tuple):
        return self.H.bracketed(
            *[self(x) for x in xs], start="(", end=")", type=_tn(xs),
        )

    def hrepr_short(self, xs: tuple):
        return self.H.bracketed(
            "...", short=True, start="(", end=")", type=_tn(xs),
        )

    # Sets

    def hrepr(self, xs: (set, frozenset)):
        return self.H.bracketed(
            *[self(x) for x in xs], start="{", end="}", type=_tn(xs),
        )

    def hrepr_short(self, xs: (set, frozenset)):
        return self.H.bracketed(
            "...", short=True, start="{", end="}", type=_tn(xs),
        )

    # Dictionaries

    def hrepr(self, obj: dict):
        return self.H.bracketed(
            *[
                self.H.pair(self(k), self(v), delimiter=": ",)
                for k, v in obj.items()
            ],
            type="dict",
            start="{",
            end="}",
            vertical=True,
        )

    def hrepr_short(self, xs: dict):
        return self.H.bracketed(
            "...", type="dict", start="{", end="}", short=True,
        )

    # Dataclasses

    def hrepr(self, obj: meta(is_dataclass)):
        return self.H.instance(
            *[
                self.H.pair(
                    self.H.atom(field.name, type="symbol"),
                    self(getattr(obj, field.name)),
                    delimiter="=",
                )
                for field in dataclass_fields(obj)
            ],
            type=_tn(obj),
            vertical=True,
        )

    def hrepr_short(self, obj: meta(is_dataclass)):
        return self.H.instance("...", type=_tn(obj), short=True,)

    # Exceptions

    def hrepr(self, obj: Exception):
        return self.H.instance["hrepr-error"](
            H.atom(str(obj.args[0])),
            *map(self, obj.args[1:]),
            type=_tn(obj),
            horizontal=True,
        )

    # Functions and methods

    def hrepr_short(self, obj: types.FunctionType):
        # types.LambdaType is types.FunctionType
        return self.H.defn("function", obj.__name__)

    def hrepr_short(self, obj: types.CoroutineType):
        return self.H.defn("coroutine", obj.__name__)

    def hrepr_short(self, obj: types.GeneratorType):
        return self.H.defn("generator", obj.__name__)

    def hrepr_short(self, obj: types.AsyncGeneratorType):
        return self.H.defn("async_generator", obj.__name__)

    def hrepr_short(self, obj: (types.MethodType, type([].__str__))):
        # Second one is types.MethodWrapperType but it's not exposed
        # in the types module in 3.6
        slf = obj.__self__
        slf = getattr(slf, "__name__", f"<{type(slf).__name__}>")
        return self.H.defn("method", f"{slf}.{obj.__name__}")

    def hrepr_short(self, obj: (type(object.__str__), type(dict.update))):
        # These are types.WrapperDescriptorType and types.MethodDescriptorType
        # but they are not exposed in the types module in 3.6
        objc = obj.__objclass__.__name__
        return self.H.defn("descriptor", f"{objc}.{obj.__name__}")

    def hrepr_short(self, obj: types.BuiltinMethodType):
        # types.BuiltinFunctionType is types.BuiltinMethodType
        slf = obj.__self__
        slf = getattr(slf, "__name__", f"<{type(slf).__name__}>")
        if slf == "builtins":
            # Let's not be redundant
            return self.H.defn("builtin", obj.__name__)
        else:
            return self.H.defn("builtin", f"{slf}.{obj.__name__}")

    def hrepr_short(self, obj: type):
        key = "metaclass" if issubclass(obj, type) else "class"
        return self.H.defn(key, obj.__name__)

    def hrepr_short(self, obj: types.ModuleType):
        return self.H.defn("module", obj.__name__)

    # Strings

    def hrepr(self, x: str):
        return self.H.atom(_encode(x), type="str")

    def hrepr_short(self, x: str):
        cutoff = self.config.string_cutoff or default_string_cutoff
        if len(x) > cutoff:
            x = x[: cutoff - 3] + "..."
        return self.H.atom(_encode(x), type="str")

    # Bytes

    def hrepr(self, x: bytes):
        cutoff = self.config.bytes_cutoff or default_bytes_cutoff
        if len(x) <= cutoff:
            return NotImplemented
        else:
            return self.H.atom(x.hex(), type="bytes")

    def hrepr_short(self, x: bytes):
        cutoff = self.config.bytes_cutoff or default_bytes_cutoff
        hx = x.hex()
        if len(hx) > cutoff:
            hx = hx[: cutoff - 3] + "..."
        return self.H.atom(hx, type="bytes")

    # Numbers

    def hrepr_short(self, x: (int, float)):
        return self.H.atom(str(x), type=_tn(x))

    # Booleans

    def hrepr_short(self, x: bool):
        return self.H.atom(str(x), value=x)

    # None

    def hrepr_short(self, x: type(None)):
        return self.H.atom(str(x), value=x)

    # Tags

    def hrepr(self, x: Tag):
        return x


def inject_reference_numbers(hcall, node, refmap):
    if isinstance(node, Tag):
        node.children = tuple(
            inject_reference_numbers(hcall, child, refmap)
            for child in node.children
        )
        refnum = refmap.get(id(node), None)
        if refnum is not None:
            return hcall.H.ref(node, num=refnum)
        else:
            return node
    else:
        return node


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
        backend,
        mixins=None,
        preprocess=None,
        postprocess=None,
        inject_references=True,
        fill_resources=True,
        **config_defaults,
    ):
        self.hclass = _mix(hclass, mixins)
        self.backend = backend
        self.preprocess = preprocess
        self.postprocess = postprocess
        self.inject_references = inject_references
        self.fill_resources = fill_resources
        self.config_defaults = config_defaults

    def copy(self):
        return type(self)(
            hclass=self.hclass,
            backend=self.backend,
            preprocess=self.preprocess,
            postprocess=self.postprocess,
            inject_references=self.inject_references,
            fill_resources=self.fill_resources,
            **self.config_defaults,
        )

    def variant(self, **options):
        return self.copy().configure(**options)

    def configure(
        self,
        *,
        hclass=None,
        mixins=None,
        backend=None,
        preprocess=ABSENT,
        postprocess=ABSENT,
        inject_references=ABSENT,
        fill_resources=ABSENT,
        **config_defaults,
    ):
        if hclass is not None:
            self.hclass = hclass
        self.hclass = _mix(self.hclass, mixins)
        if backend is not None:
            self.backend = backend
        if preprocess is not ABSENT:
            self.preprocess = preprocess
        if postprocess is not ABSENT:
            self.postprocess = postprocess
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
                H=H,
                config=Config(self.config_defaults),
                preprocess=self.preprocess,
                postprocess=self.postprocess,
            )
            if len(objs) == 1:
                rval = hcall(objs[0])
            else:
                rval = H.inline(*map(hcall, objs))
            if self.inject_references:
                rval = inject_reference_numbers(
                    hcall, rval, hcall.state.make_refmap()
                )
            if self.fill_resources:
                rval = rval.fill(resources=hcall.global_resources())
            rval = self.backend(rval)
            return rval
