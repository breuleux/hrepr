import textwrap
from collections import Counter
from dataclasses import fields as dataclass_fields
from dataclasses import is_dataclass

from ovld import OvldCall, OvldMC, meta, ovld

from . import std
from .h import HTML, H, Tag, css_hrepr

default_string_cutoff = 20
default_bytes_cutoff = 20


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
        if not cfg:
            return self
        else:
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

    def __init__(self, H=H, config=None, master=None):
        self.H = H
        if config is None:
            config = Config()
        self.config = config
        self.master = master or self
        self.state = master.state if master else HreprState()

    def with_config(self, config):
        if not config:
            return self
        else:
            cfg = self.config.with_config(config)
            return type(self)(H=self.H, config=cfg, master=self.master)

    def ref(self, obj, loop=False):
        num = self.state.get_ref(id(obj))
        sym = "⟳" if loop else "#"
        ref = self.H.span["hrepr-ref"](sym, num)
        if self.config.shortref:
            return ref
        else:
            return self.H.div["hrepr-refbox"](ref("="), self.hrepr_short(obj))

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
            return obj.__hrepr__(self, self.H)
        else:
            return NotImplemented

    @ovld
    def hrepr_short(self, obj: object):
        if hasattr(obj, "__hrepr_short__"):
            return obj.__hrepr_short__(self, self.H)
        else:
            clsn = type(obj).__name__
            rval = self.H.span[f"hreprs-{clsn}"]("<", clsn, ">")
            self.state.register(id(obj), rval)
            return rval

    def __call__(self, obj, **config):
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

        # Pop object from the stack
        self.state.depth -= 1
        self.state.stack[ido] -= 1

        # Collect resources for this object
        cls = type(obj)
        resources = self.hrepr_resources[cls](cls)
        rval = rval.fill(resources=resources)

        return rval


class StdHrepr(Hrepr):
    def global_resources(self):
        return {self.H.style(css_hrepr)}

    # Lists

    def hrepr(self, xs: list):
        return std.iterable(self, xs, before="[", after="]")

    def hrepr_short(self, xs: list):
        return self.H.span["hreprs-list"]("[...]")

    # Tuples

    def hrepr(self, xs: tuple):
        return std.iterable(self, xs, before="(", after=")")

    def hrepr_short(self, xs: tuple):
        return self.H.span["hreprs-tuple"]("(...)")

    # Sets

    def hrepr(self, xs: (set, frozenset)):
        return std.iterable(self, xs, before="{", after="}")

    def hrepr_short(self, xs: (set, frozenset)):
        cls = type(xs).__name__
        return self.H.span[f"hreprs-{cls}"]("{...}")

    # Dictionaries

    def hrepr(self, obj: dict):
        cls = type(obj).__name__
        return std.instance(
            self,
            ("{", "}"),
            list(obj.items()),
            cls=f"hreprt-{cls}",
            quote_string_keys=True,
            short=self.config.mapping_layout == "h",
        )

    def hrepr_short(self, xs: dict):
        cls = type(xs).__name__
        return self.H.span[f"hreprs-{cls}"]("{...}")

    # Dataclasses

    def hrepr(self, obj: dataclass_without("__hrepr__")):
        cls = type(obj).__name__
        props = {
            field.name: getattr(obj, field.name)
            for field in dataclass_fields(obj)
        }
        return std.instance(
            self,
            cls,
            props,
            cls=f"hreprt-{cls}",
            quote_string_keys=False,
            delimiter="=",
        )

    def hrepr_short(self, xs: dataclass_without("__hrepr_short__")):
        cls = type(xs).__name__
        return self.H.span[f"hreprs-{cls}", "hrepr-short-instance"](
            f"{cls} ..."
        )

    # Strings

    def hrepr(self, x: str):
        cutoff = self.config.string_cutoff or default_string_cutoff
        if len(x) <= cutoff:
            return NotImplemented
        else:
            return self.H.span[f"hreprt-str"](x)

    def hrepr_short(self, x: str):
        cutoff = self.config.string_cutoff or default_string_cutoff
        return self.H.span[f"hreprt-str"](
            textwrap.shorten(x, cutoff, placeholder="...")
        )

    # Bytes

    def hrepr(self, x: bytes):
        cutoff = self.config.bytes_cutoff or default_bytes_cutoff
        if len(x) <= cutoff:
            return NotImplemented
        else:
            return self.H.span[f"hreprt-bytes"](x.hex())

    def hrepr_short(self, x: bytes):
        cutoff = self.config.bytes_cutoff or default_bytes_cutoff
        hx = x.hex()
        if len(hx) > cutoff:
            hx = hx[: cutoff - 3] + "..."
        return self.H.span[f"hreprt-bytes"](hx)

    # Numbers

    def hrepr_short(self, x: (int, float)):
        cls = type(x).__name__
        return self.H.span[f"hreprt-{cls}"](str(x))
        # return std.standard(self, x)

    # Booleans

    def hrepr_short(self, x: bool):
        return self.H.span[f"hreprv-{x}"](str(x))

    # None

    def hrepr_short(self, x: type(None)):
        return self.H.span[f"hreprv-{x}"](str(x))

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
            ref = hcall.H.span["hrepr-ref"]("#", refnum)
            return hcall.H.div["hrepr-refbox"](ref("="), node)
        else:
            return node
    else:
        return node


class Interface:
    def __init__(self, cls, inject_references=True, fill_resources=True):
        self._hcls = cls
        self.inject_references = inject_references
        self.fill_resources = fill_resources

    def hrepr(self, obj, **config):
        hcall = self._hcls(H=H, config=Config(config))
        rval = hcall(obj)
        if self.inject_references:
            rval = inject_reference_numbers(
                hcall, rval, hcall.state.make_refmap()
            )
        if self.fill_resources:
            rval = rval.fill(resources=hcall.global_resources())
        return rval


hrepr = StdHrepr.make_interface().hrepr
