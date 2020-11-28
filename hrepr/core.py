import textwrap
from collections import Counter
from dataclasses import fields as dataclass_fields
from dataclasses import is_dataclass

from ovld import OvldCall, OvldMC, meta, ovld

from . import std
from .h import HTML, H, Tag, css_hrepr
from .std import standard_html

default_string_cutoff = 20
default_bytes_cutoff = 20


def _tn(x):
    return type(x).__name__


def dataclass_without(prop):
    @meta
    def fn(cls):
        return is_dataclass(cls) and not hasattr(cls, prop)

    return fn


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

    def __hrepr__(self, H, hrepr):  # pragma: no cover
        return hrepr.stdrepr_object("Config", self.__dict__.items())


# class ResourceAccumulator:
#     def __init__(self, acq):
#         self.consulted = set()
#         self.resources = set()
#         self.spent = set()
#         self.acq = acq

#     def acquire(self, cls):
#         if cls not in self.consulted:
#             self.consulted.add(cls)
#             resources = self.acq(cls)
#             resources -= self.spent
#             self.resources |= resources

#     def dump(self):
#         rval = self.resources
#         self.spent |= self.resources
#         self.resources.clear()
#         return rval


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
            return type(self)(H=self.H, config=cfg, master=self.master)

    def ref(self, obj, loop=False):
        num = self.state.get_ref(id(obj))
        ref = self.H.ref(loop=loop, num=num)
        if not self.config.shortref:
            ref = ref(self.hrepr_short(obj))
        return ref

    def global_resources(self):  # pragma: no cover
        return set()

    @ovld
    def hrepr_resources(self, cls: object):
        if hasattr(cls, "__hrepr_resources__"):
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
        if hasattr(obj, "__hrepr__"):
            return obj.__hrepr__(self.H, self)
        else:
            return NotImplemented

    @ovld
    def hrepr_short(self, obj: object):
        if hasattr(obj, "__hrepr_short__"):
            return obj.__hrepr_short__(self.H, self)
        else:
            clsn = _tn(obj)
            rval = self.H.span[f"hreprs-{clsn}"]("<", clsn, ">")
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

        return rval


class StdHrepr(Hrepr):
    def __init__(self, *, std=std, **kw):
        super().__init__(**kw)
        self.std = std

    def global_resources(self):
        return {self.H.style(css_hrepr)}

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

    def hrepr(self, obj: dataclass_without("__hrepr__")):
        return self.H.instance(
            *[
                self.H.pair(
                    self.H.symbol(field.name),
                    self(getattr(obj, field.name)),
                    delimiter="=",
                )
                for field in dataclass_fields(obj)
            ],
            type=_tn(obj),
            vertical=True,
        )

    def hrepr_short(self, obj: dataclass_without("__hrepr_short__")):
        return self.H.instance(f"...", type=_tn(obj), short=True,)

    # Strings

    def hrepr(self, x: str):
        cutoff = self.config.string_cutoff or default_string_cutoff
        if len(x) <= cutoff:
            return NotImplemented
        else:
            return self.H.atom(x, type="str")

    def hrepr_short(self, x: str):
        cutoff = self.config.string_cutoff or default_string_cutoff
        return self.H.atom(
            textwrap.shorten(x, cutoff, placeholder="..."), type="str",
        )

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


class Interface:
    def __init__(self, hclass, inject_references=True, fill_resources=True):
        self._hcls = hclass
        self.inject_references = inject_references
        self.fill_resources = fill_resources

    def __call__(
        self,
        *objs,
        hclass=None,
        mixins=None,
        preprocess=None,
        postprocess=None,
        backend=standard_html,
        **config,
    ):
        hcls = hclass or self._hcls
        if mixins:
            if isinstance(mixins, type):
                mixins = [mixins]
            hcls = hcls.create_subclass(*mixins)
        hcall = hcls(
            H=H,
            config=Config(config),
            preprocess=preprocess,
            postprocess=postprocess,
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
        rval = backend(rval)
        return rval


hrepr = StdHrepr.make_interface()
