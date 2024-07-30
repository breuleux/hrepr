import pytest
from hrepr import resource
from hrepr.resource import JSFunction as JSF
from hrepr.resource import Resource

from .common import one_test_per_assert

embed_key = "0123456789abcdeffedcba9876543210"


@pytest.fixture(autouse=True)
def reset_registry():
    resource.embed_key = embed_key
    resource.registry.reset()


def test_Resource_str():
    assert str(Resource(123)) == f"[{embed_key}:0]"


def test_Resource_str_variant():
    assert str(Resource("hello world", variant="x")) == f"[{embed_key}:x0]"


@one_test_per_assert
def test_JSFunction():
    assert JSF("foo", "foo + 1").code == "((foo) => foo + 1)"
    assert JSF(("foo", "bar"), "foo + bar").code == "((foo, bar) => foo + bar)"
    assert JSF(["foo", "bar"], "foo + bar").code == "((foo, bar) => foo + bar)"
    assert JSF("foo", "return foo + 1").code == "((foo) => { return foo + 1 })"
    assert JSF("foo", "foo + 1;").code == "((foo) => { foo + 1; })"
    assert (
        JSF("foo", "foo + 1", expression=False).code == "((foo) => { foo + 1 })"
    )
