from dataclasses import dataclass


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
