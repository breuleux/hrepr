from types import FunctionType

import pytest
from ovld import ovld

from hrepr import H, resource
from hrepr.resource import Embedder, Resource, registry

embed_key = "0123456789abcdeffedcba9876543210"


@pytest.fixture(autouse=True)
def reset_registry():
    resource.embed_key = embed_key
    resource.registry.reset()


@pytest.fixture
def embedder():
    return MyEmbedder(registry)


class MyEmbedder(Embedder):
    @ovld
    def embed(self, obj: int, resource, tag, attr):
        return f"2 * {obj//2} + {obj%2}"

    @ovld
    def embed(self, obj: FunctionType, resource, tag, attr):
        if attr == "onclick":
            return f"{obj.__name__}()"
        else:
            return f"{obj.__name__}"


def test_Resource_str():
    assert str(Resource(123)) == f"[{embed_key}:0]"


def test_Resource_str_variant():
    assert str(Resource("hello world", variant="x")) == f"[{embed_key}:x0]"


def test_embed(embedder):
    resource = Resource(101)
    text = f"x = {resource}"
    assert embedder(H.div(), None, text) == "x = 2 * 50 + 1"
