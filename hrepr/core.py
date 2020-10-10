
import textwrap
from collections import Counter
from dataclasses import is_dataclass, fields as dataclass_fields

from ovld import meta, ovld, OvldCall, OvldMC
from .h import css_hrepr, H, HTML, Tag
from . import std


SHORT = object()
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

    # def __call__(self, **cfg):
    #     return self.with_config(cfg)

    def with_config(self, cfg):
        if not cfg:
            return self
        elif self.__dict__.keys() == cfg.keys():
            return Config(cfg, self._parent)
        else:
            return Config(cfg, self)

    def __getattr__(self, attr):
        # Only triggers for attributes not in __dict__
        if attr.startswith("_"):
            return getattr(super(), attr)
        elif self._parent:
            return getattr(self._parent, attr)
        return None

    def __hrepr__(self, H, hrepr):
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
    def __init__(self, resources=set()):
        self.types_seen = set()
        self.resources = set(resources)
        self.stack = Counter()
        self.registry = {}
        self.depth = -1
        self.refs = {}

    def get_ref(self, objid):
        return self.refs.setdefault(objid, len(self.refs) + 1)

    def registered(self, objid):
        return objid in self.registry

    def register(self, objid, value):
        self.registry[objid] = value

    def make_refmap(self):
        rval = {}
        for objid, label in self.refs.items():
            rval[id(self.registry[objid])] = label
        return rval


class Hrepr(metaclass=OvldMC):

    def __init__(self, H=H, config=None, master=None):
        self.H = H
        if config is None:
            config = Config()
        self.config = config
        self.master = master or self
        self.state = (
            master.state
            if master
            else HreprState(self.global_resources())
        )

    def with_config(self, config):
        if not config:
            return self
        else:
            cfg = self.config.with_config(config)
            return type(self)(H=self.H, config=cfg, master=self.master)

    def ref(self, obj, loop=False):
        # breakpoint()
        num = self.state.get_ref(id(obj))
        sym = "⟳" if loop else "#"
        ref = self.H.span["hrepr-ref"](sym, num)
        if self.config.shortref:
            return ref
        else:
            return self.H.div["hrepr-refbox"](ref("="), self.hrepr_short(obj))
            # short = self.hrepr_short(obj)
            # if short is NotImplemented:
            #     short = self.default_hrepr_short(obj)
            # return self.H.div["hrepr-refbox"](ref("="), short)

    def global_resources(self):
        return set()

    # def default_hrepr_resources(self, cls):
    #     return None

    def default_hrepr(self, obj):
        clsn = type(obj).__name__
        return self.H.span[f"hreprt-{clsn}"](str(obj))

    def default_hrepr_short(self, obj):
        clsn = type(obj).__name__
        return self.H.span[f"hreprs-{clsn}"]("<", clsn, ">")

    @ovld
    def hrepr_resources(self, cls: object):
        if hasattr(cls, "__hrepr_resources__"):
            return cls.__hrepr_resources__(self.H)

    @ovld.dispatch
    def hrepr(ovldcall, obj):
        self = ovldcall.obj
        rval = ovldcall.resolve(obj)(obj)
        if rval is SHORT:
            return self.hrepr_short(obj)
        elif rval is NotImplemented:
            rval = self.hrepr_short.resolve(obj)(obj)
            if rval is NotImplemented:
                rval = self.default_hrepr(obj)
            else:
                return rval
        self.state.register(id(obj), rval)
        return rval

    def hrepr(self, obj: object):
        if hasattr(obj, "__hrepr__"):
            return obj.__hrepr__(self, self.H)
        else:
            return NotImplemented

    @ovld.dispatch
    def hrepr_short(ovldcall, obj):
        self = ovldcall.obj
        rval = ovldcall.resolve(obj)(obj)
        if rval is NotImplemented:
            return self.default_hrepr_short(obj)
        else:
            return rval

    def hrepr_short(self, obj: object):
        if hasattr(obj, "__hrepr_short__"):
            return obj.__hrepr_short__(self, self.H)
        else:
            return NotImplemented

    def __call__(self, obj, **config):
        self.state.skip_default = False
        runner = self.with_config(config)
        ido = id(obj)
        if self.state.stack[ido]:
            return runner.ref(obj, loop=True)

        if self.state.registered(ido) and not runner.config.norefs:
            return runner.ref(obj)

        # Collect resources for this object
        cls = type(obj)
        if cls not in self.state.types_seen:
            self.state.types_seen.add(cls)
            resources = self.hrepr_resources[cls](cls)
            if resources:
                if not isinstance(resources, (tuple, list, set, frozenset)):
                    self.state.resources.add(resources)
                else:
                    self.state.resources.update(resources)

        # Push object on the stack to detect circular references
        self.state.stack[ido] += 1
        self.state.depth += 1

        if (runner.config.max_depth is not None
            and self.state.depth >= runner.config.max_depth):
            rval = runner.hrepr_short(obj)
        else:
            rval = runner.hrepr(obj)

        # Pop object from the stack
        self.state.depth -= 1
        self.state.stack[ido] -= 1
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
        return self.H.span[f"hreprs-{cls}", "hrepr-short-instance"](f"{cls} ...")

    # Strings

    def hrepr(self, x: str):
        cutoff = self.config.string_cutoff or default_string_cutoff
        if len(x) <= cutoff:
            return SHORT
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
            return SHORT
        else:
            return self.H.span[f"hreprt-bytes"](x.hex())

    def hrepr_short(self, x: bytes):
        cutoff = self.config.bytes_cutoff or default_bytes_cutoff
        hx = x.hex()
        if len(hx) > cutoff:
            hx = hx[:cutoff - 3] + "..."
        return self.H.span[f"hreprt-bytes"](hx)

    # Numbers

    def hrepr_short(self, x: (int, float)):
        cls = type(x).__name__
        return self.H.span[f"hreprt-{cls}"](str(x))
        # return std.standard(self, x)

    # Booleans

    def hrepr_short(self, x: bool):
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


def hrepr(obj, **config):
    hcall = StdHrepr(H=H, config=Config(config))
    rval = hcall(obj)
    rval = inject_reference_numbers(hcall, rval, hcall.state.make_refmap())
    rval.resources = hcall.state.resources
    return rval
