import re
from collections import deque
from dataclasses import dataclass

from . import h
from .textgen import Sequence


class CodeWrapper:
    is_async = False

    def wrap(self, current):  # pragma: no cover
        raise NotImplementedError()

    def __call__(self, current):
        result = self.wrap(current)
        if isinstance(result, (list, tuple)):
            result = Sequence(*result)
        return result


class Await(CodeWrapper):
    is_async = True

    def wrap(self, current):
        return ["(await ", current, ")"]


@dataclass
class Eval(CodeWrapper):
    code: str
    exec: bool
    is_async: bool = None

    def __post_init__(self):
        if self.is_async is None:
            self.is_async = bool(
                re.match(pattern=r"\bawait\b", string=self.code)
            )

    def wrap(self, current):
        return [
            "(function () { ",
            "" if self.exec else "return ",
            self.code,
            " }).bind(",
            current,
            ")()",
        ]


@dataclass
class Wrap(CodeWrapper):
    before: str = ""
    after: str = ""

    def wrap(self, current):
        return [self.before, current, self.after]


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
        selector=None,
        object=None,
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

        if selector:
            assert not namespace
            assert not _path
            sanitized = selector.replace("\\", "\\\\").replace('"', r"\"")
            _path.append(f'document.querySelector("{sanitized}")')

        if object:
            assert not selector
            assert not namespace
            assert not _path
            sanitized = object.replace("\\", "\\\\").replace('"', r"\"")
            _path.append(
                f'(x => x.__object || x)(document.querySelector("{sanitized}"))'
            )
            _path.append(Await())

        if _data is None:
            _data = JData(
                namespace=namespace,
                src=src,
                code=code,
                stylesheet=stylesheet,
            )

        self._data = _data
        self._path = _path
        self._model_attributes = None
        self._returns = None
        self._async = None
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

    def _is_async(self):
        if self._async is not None:
            return self._async
        is_async = False
        for p in self._path:
            if isinstance(p, CodeWrapper):
                is_async = p.is_async
            elif isinstance(p, (list, tuple)):
                is_async = any(isinstance(x, J) and x._is_async() for x in p)
            if is_async:
                break
        self._async = is_async
        return is_async

    def _append_path(self, *extra):
        return type(self)(_data=self._data, _path=[*self._path, *extra])

    def await_(self):  # pragma: no cover
        return self._append_path(Await())

    def wrap_code(self, before="", after=""):
        return self._append_path(Wrap(before=before, after=after))

    def thunk(self):
        asynk = "async " if self._is_async() else ""
        return self.wrap_code(f"({asynk}()=>", ")")

    def eval(self, code="this"):
        return self._append_path(Eval(code, exec=False))

    def exec(self, code="this"):
        return self._append_path(Eval(code, exec=True))

    def as_node(self, *args, **kwargs):
        from .h import H

        return H.construct(*args, **kwargs, constructor=self)

    def as_page(self):
        return self.as_node().as_page()

    def __getattr__(self, attr):
        if attr.startswith("__") and attr.endswith("__"):  # pragma: no cover
            raise AttributeError(attr)
        return self._append_path(attr)

    __getitem__ = __getattr__

    def __call__(self, *args, **kwargs):
        if kwargs:
            args = (*args, kwargs)
        return self._append_path(args)
