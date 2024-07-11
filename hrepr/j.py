from collections import deque
from dataclasses import dataclass

from . import h


@dataclass
class Returns:
    value: object


@dataclass
class JData:
    namespace: str = None
    src: str = None
    code: str = None
    stylesheet: str = None


class J:
    def __init__(
        self,
        *,
        namespace=None,
        module=None,
        src=None,
        code=None,
        stylesheet=None,
        _data=None,
        _path=None,
    ):
        _path = _path or []
        if module:
            assert not namespace
            namespace = module
            assert not _path
            _path.append("default")

        if _data is None:
            _data = JData(
                namespace=namespace,
                src=src,
                code=code,
                stylesheet=stylesheet,
            )

        self._data = _data
        self._path = _path
        self._returns = None
        self._serial = next(h.current_id)

    def _get_id(self):
        ret = self._get_returns()
        if not ret:
            return f"H{self._serial}"
        elif isinstance(ret, J):
            return ret._get_id()
        else:
            return ret.id

    def _get_returns(self):
        if self._returns is not None:
            return self._returns

        to_process = deque(self._path)
        while to_process:
            x = to_process.popleft()
            if isinstance(x, (list, tuple)):
                to_process.extend(x)
            elif isinstance(x, Returns):
                self._returns = x.value
                return x.value
            elif isinstance(x, J):
                r = x._get_returns()
                if r:
                    self._returns = r
                    return r

        self._returns = False
        return False

    def __getattr__(self, attr):
        if attr.startswith("__") and attr.endswith("__"):  # pragma: no cover
            raise AttributeError(attr)
        return type(self)(
            _data=self._data,
            _path=[*self._path, attr],
        )

    __getitem__ = __getattr__

    def __call__(self, *args, **kwargs):
        if kwargs:
            args = (*args, kwargs)
        return type(self)(
            _data=self._data,
            _path=[*self._path, args],
        )
