
from hrepr import hrepr, StdHrepr, H

from .common import one_test_per_assert


class Banana:
    def __init__(self, taste):
        self.taste = taste

    def __hrepr__(self, hrepr, H):
        return H.span["banana"](hrepr(self.taste))

    def __hrepr_short__(self, hrepr, H):
        return H.span["banana"]("B A N A N A")


class Katana:
    def __hrepr__(self, hrepr, H):
        return H.b(hrepr.config.katana or "n/a")


class KatanaWrapper:
    def __init__(self, katana, value):
        self.katana = katana
        self.value = value

    def __hrepr__(self, hrepr, H):
        return hrepr(self.katana, katana=self.value)


class CustomHrepr(StdHrepr):
    def hrepr(self, x: int):
        return self.H.span["myint"](str(-x))


chrepr = CustomHrepr()


def test_override_int():
    assert chrepr(123) == H.span["myint"]("-123")


@one_test_per_assert
def test_dunder():
    assert hrepr(Banana("starchy")) == H.span["banana"](H.span["hreprt-str"]("starchy"))
    assert hrepr(Banana("starchy"), max_depth=0) == H.span["banana"]("B A N A N A")
    assert chrepr(Banana(10)) == H.span["banana"](H.span["myint"]("-10"))


@one_test_per_assert
def test_config():
    assert hrepr(Katana()) == H.b("n/a")
    assert hrepr(Katana(), katana=1234) == H.b(1234)
    assert hrepr(KatanaWrapper(Katana(), 9000)) == H.b(9000)
