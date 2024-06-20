from dataclasses import dataclass
from typing import Optional

from .h import Tag


@dataclass
class Into:
    element: Tag


@dataclass
class Module:
    module: str
    symbol: Optional[str] = None
    varname: Optional[str] = None
    namespace: bool = False


@dataclass
class Script:
    src: str
    symbol: Optional[str] = None


@dataclass
class Code:
    code: str
    symbol: Optional[str] = None


class J:
    def __init__(
        self,
        *,
        module=None,
        src=None,
        code=None,
        namespace=None,
        symbol=None,
        path=None,
    ):
        self.module = module
        self.namespace = namespace
        self.src = src
        self.code = code
        self.symbol = symbol
        self.path = path or []

    def __getattr__(self, attr):
        if attr.startswith("__") and attr.endswith("__"):  # pragma: no cover
            raise AttributeError(attr)
        return type(self)(
            module=self.module,
            namespace=self.namespace,
            src=self.src,
            code=self.code,
            symbol=self.symbol,
            path=[*self.path, attr],
        )

    __getitem__ = __getattr__

    def __call__(self, *args, **kwargs):
        if kwargs:
            args = (*args, kwargs)
        return type(self)(
            module=self.module,
            namespace=self.namespace,
            src=self.src,
            code=self.code,
            symbol=self.symbol,
            path=[*self.path, args],
        )
