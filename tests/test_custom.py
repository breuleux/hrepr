import pytest
from hrepr import H, StdHrepr
from ovld import extend_super

from .common import one_test_per_assert

hrepr = StdHrepr.make_interface(fill_resources=False)


class Banana:
    def __init__(self, taste):
        self.taste = taste

    def __hrepr__(self, H, hrepr):
        return H.span["banana"](hrepr(self.taste))

    def __hrepr_short__(self, H, hrepr):
        return H.span["banana"]("B A N A N A")


class Katana:
    def __hrepr__(self, H, hrepr):
        return H.b(hrepr.config.katana or "n/a")


class KatanaWrapper:
    def __init__(self, katana, value):
        self.katana = katana
        self.value = value

    def __hrepr__(self, H, hrepr):
        return hrepr(self.katana, katana=self.value)


class CustomHrepr(StdHrepr):
    @extend_super
    def hrepr(self, x: int):
        return self.H.span["myint"](str(-x))


class Plantain(Banana):
    @classmethod
    def __hrepr_resources__(cls, H):
        return H.style(".banana { color: yellow; }")


class Evil:
    def __hrepr__(self, H, hrepr):
        return "EVIL"


chrepr = CustomHrepr.make_interface(fill_resources=False)


def test_override_int():
    assert chrepr(123) == H.span["myint"]("-123")


@one_test_per_assert
def test_dunder():
    assert hrepr(Banana("starchy")) == H.span["banana"](
        H.span["hreprt-str"]("starchy")
    )
    assert hrepr(Banana("starchy"), max_depth=0) == H.span["banana"](
        "B A N A N A"
    )
    assert hrepr(Plantain("starchy")) == H.span["banana"](
        H.span["hreprt-str"]("starchy")
    ).fill(resources=H.style(".banana { color: yellow; }"))
    assert chrepr(Banana(10)) == H.span["banana"](H.span["myint"]("-10"))


@one_test_per_assert
def test_config():
    assert hrepr(Katana()) == H.b("n/a")
    assert hrepr(Katana(), katana=1234) == H.b(1234)
    assert hrepr(KatanaWrapper(Katana(), 9000)) == H.b(9000)


def test_bad_return_type():
    with pytest.raises(TypeError):
        hrepr(Evil())


class MyIntRepr:
    @extend_super
    def hrepr_resources(self, cls: int):
        return self.H.style(".my-integer { color: fuchsia; }")

    @extend_super
    def hrepr(self, n: int):
        return self.H.span["my-integer"]("The number ", str(n))


def test_mixin():
    assert hrepr(1, mixins=MyIntRepr) == H.span["my-integer"](
        "The number ", "1"
    ).fill(resources=H.style(".my-integer { color: fuchsia; }"))
