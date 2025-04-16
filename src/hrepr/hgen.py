import json
import re
from collections import deque
from dataclasses import dataclass, field
from html import escape
from pathlib import Path
from typing import Callable, Optional, Union

from ovld import OvldBase, recurse
from ovld.dependent import Code, ParametrizedDependentType

from . import resource
from .h import H, Tag, gensym
from .j import CodeWrapper, J, Returns
from .textgen import Breakable, Sequence, Text, TextFormatter, join

here = Path(__file__).parent
constructor_lib = H.script((here / "hlib.js").read_text())
css_nbreset = H.style((here / "style/nbreset.css").read_text())


class HasNodeName(ParametrizedDependentType):
    exclusive_type = True
    keyable_type = False

    def default_bound(self, name):
        return Tag

    def check(self, value):  # pragma: no cover
        # codegen/keygen/get_key will take care of it
        return value.name == self.parameter

    @classmethod
    def keygen(self):  # pragma: no cover
        return Code("$arg.name")

    def get_keys(self):  # pragma: no cover
        return [self.parameter]

    def codegen(self):
        return Code("($arg.name == $p)", p=self.parameter)


_void_tags = {
    "area",
    "base",
    "br",
    "col",
    "command",
    "embed",
    "hr",
    "img",
    "input",
    "keygen",
    "link",
    "meta",
    "param",
    "source",
    "track",
    "wbr",
    "!DOCTYPE",
}


@dataclass
class ScriptAccumulator:
    returns: Optional[object] = None
    scripts: list = field(default_factory=list)
    modules: list = field(default_factory=list)
    codes: list = field(default_factory=list)
    styles: list = field(default_factory=list)


@dataclass
class BlockGenerator(OvldBase):
    global_generator: "HTMLGenerator"
    hrepr: Callable = None
    result: Tag = None
    resources: deque = field(default_factory=deque)
    script_accumulator: Optional[ScriptAccumulator] = None
    extra: deque = field(default_factory=deque)
    processed_resources: list = None
    processed_extra: list = None

    #############
    # Utilities #
    #############

    @property
    def constructor_lib(self):
        return constructor_lib

    def expand_resources(self, value, embed):
        def sub(m):
            res = resource.registry.resolve(int(m.groups()[0]))
            return self.expand_resources(embed(res.obj), embed)

        return re.sub(
            pattern=rf"\[{resource.embed_key}:([0-9]+)\]",
            string=str(value),
            repl=sub,
        )

    def represent_node_generic(
        self, node, open=None, close=None, node_embed=None
    ):
        self.resources.extend(node.resources)

        open = node.name if open is None else open
        close = (node.name not in _void_tags) if close is None else close

        node_embed = node_embed or self.node_embed

        attributes = {k: self.attr_embed(v) for k, v in node.attributes.items()}

        attr = "".join(
            f" {k}" if v is True else f' {k}="{escape(v)}"'
            for k, v in attributes.items()
            if v is not None and v is not False
        )

        children = list(map(node_embed, node.children))

        if open:
            if close:
                return Breakable(
                    start=f"<{open}{attr}>",
                    body=children,
                    end=f"</{open}>",
                )
            else:
                assert not children
                return Text(f"<{open}{attr} />")
        else:
            return Breakable(start=None, body=children, end=None)

    #####################
    # node_embed method #
    #####################

    def node_embed(self, node: str):
        return escape(node)

    def node_embed(self, node: Union[int, float]):
        return str(node)

    def node_embed(self, node: TextFormatter):
        return node

    def node_embed(self, node: HasNodeName["script"]):
        return self.represent_node_generic(
            node=node,
            node_embed=self.script_node_embed,
        )

    def node_embed(self, node: HasNodeName["style"]):
        return self.represent_node_generic(
            node=node,
            node_embed=self.raw_node_embed,
        )

    def node_embed(self, node: HasNodeName["raw"]):
        return self.represent_node_generic(
            node=node,
            open=False,
            close=False,
            node_embed=self.raw_node_embed,
        )

    def node_embed(self, node: HasNodeName["inline"]):
        return self.represent_node_generic(
            node=node,
            open=False,
            close=False,
        )

    def node_embed(self, node: HasNodeName["construct"]):
        if node.children:  # pragma: no cover
            raise Exception("<construct> nodes should not have children")
        j = node.attributes["constructor"]
        j._model_attributes = {
            k: v
            for k, v in node.attributes.items()
            if k != "constructor" and not k.startswith("-")
        }
        return recurse(j)

    def node_embed(self, node: Tag):
        return self.represent_node_generic(node=node)

    def node_embed(self, node: J):
        assert not self.script_accumulator
        self.script_accumulator = ScriptAccumulator()

        embedded = self.js_embed(node)

        lines = [
            f"const obj = {embedded};",
            "$$INTO.__object.__resolve(obj);",
        ]

        element = self.script_accumulator.returns
        if isinstance(element, Tag):
            element = element.ensure_id()
            replace_line = ""
            wid = element.id
        elif isinstance(element, J):
            replace_line = ""
            wid = element._get_id()
        elif element is None:
            wid = f"H{node._serial}"
            element = H.placeholder(id=wid)
            replace_line = "$$HREPR.swap($$INTO, obj);"
        else:  # pragma: no cover
            raise TypeError("returns() expression must be a Tag or J object.")

        if isinstance(element, Tag) and node._model_attributes:
            element = element(**node._model_attributes)

        async_txt = "async " if node._is_async() else ""
        lines = [
            f"$$HREPR.run({self.js_embed(list(set(self.script_accumulator.scripts)))},'#{wid}',{async_txt}()=>{{",
            *lines,
            replace_line,
            "});",
        ]

        self.extra.append(H.script(f"$$HREPR.prepare({self.js_embed(wid)});"))

        into_line = (
            f"const $$INTO = document.getElementById({self.js_embed(wid)});"
        )
        lines = [into_line, *lines]

        for module, symbol, varname in self.script_accumulator.modules:
            if symbol:
                line = f"import {{ {symbol} as {varname} }} from {self.js_embed(module)};"
            else:
                line = f"import {varname} from {self.js_embed(module)};"
            lines = [line, *lines]

        for code in self.script_accumulator.codes:
            self.resources.append(H.script(code))

        for sty in self.script_accumulator.styles:
            self.resources.append(sty)

        if clib := self.constructor_lib:
            self.resources.append(clib)

        self.script_accumulator = None

        result = recurse(element)
        self.extra.append(H.script("\n".join(lines), type="module"))
        return result

    def node_embed(self, node: type(None)):
        return ""

    def node_embed(self, node: object):
        if hasattr(node, "__h__"):
            return recurse(node.__h__())
        elif self.hrepr:
            return recurse(self.hrepr(node))
        else:
            return str(node)

    ###################################
    # Alternate node embedders method #
    ###################################

    def raw_node_embed(self, text: str):
        return text

    def script_node_embed(self, text: str):
        return self.expand_resources(text, self.js_embed)

    #####################
    # attr_embed method #
    #####################

    def attr_embed(self, value: bool):
        if value is False:
            return None
        elif value is True:
            return value

    def attr_embed(self, value: Union[str, int, float]):
        return str(value)

    def attr_embed(self, elements: Union[list, tuple, set, frozenset]):
        return " ".join(recurse(elem) for elem in elements)

    def attr_embed(self, style: dict):
        return "".join(f"{k}:{v};" for k, v in style.items())

    def attr_embed(self, expr: resource.JSExpression):
        return self.expand_resources(expr.code, self.js_embed)

    def attr_embed(self, t: Tag):
        tag_id = t.get_attribute("id", None)
        if not tag_id:
            raise ValueError(f"Cannot embed <{t.name}> element without an id.")
        return f"#{tag_id}"

    def attr_embed(self, x: object):
        if hasattr(x, "__attr_embed__"):
            return x.__attr_embed__(self)
        else:
            raise TypeError(
                f"Resources of type {type(x).__name__} cannot be serialized as an attribute."
            )

    ###################
    # js_embed method #
    ###################

    def js_embed(self, d: dict):
        return Breakable(
            start="{",
            body=join(
                [Sequence(recurse(k), ": ", recurse(v)) for k, v in d.items()],
                sep=", ",
            ),
            end="}",
        )

    def js_embed(self, seq: Union[list, tuple]):
        return Breakable(
            start="[",
            body=join(map(self.js_embed, seq), sep=", "),
            end="]",
        )

    def js_embed(self, x: Union[int, float, str, bool, type(None)]):
        return Text(json.dumps(x))

    def js_embed(self, expr: resource.JSExpression):
        return expr.code

    def js_embed(self, t: Tag):
        innerhtml = self.global_generator.to_string(t)
        return f"$$HREPR.fromHTML({recurse(innerhtml)})"

    def js_embed(self, j: J):
        jd = j._data

        if not j._path or not isinstance(j._path[0], str):
            raise Exception(
                "The J constructor should first be invoked with an attribute or a selector."
            )

        symbol, *path = j._path

        if jd.stylesheet is not None:
            styles = (
                jd.stylesheet
                if isinstance(jd.stylesheet, Sequence)
                else [jd.stylesheet]
            )
            self.script_accumulator.styles.extend(
                [
                    src
                    if isinstance(src, Tag)
                    else H.link(rel="stylesheet", href=src)
                    for src in styles
                ]
            )
        if jd.namespace is not None:
            varname = gensym(symbol)
            self.script_accumulator.modules.append(
                (
                    jd.namespace,
                    None if symbol == "default" else symbol,
                    varname,
                )
            )
        elif jd.src is not None:
            varname = symbol
            src = jd.src if isinstance(jd.src, (list, tuple)) else [jd.src]
            self.script_accumulator.scripts.extend(src)
        elif jd.code is not None:
            varname = symbol
            self.script_accumulator.codes.append(jd.code)
        else:
            varname = symbol

        assert varname is not None

        result = varname
        prev_result = varname
        last_symbol = None

        for entry in path:
            if isinstance(entry, str):
                prev_result = result
                last_symbol = entry
                result = Sequence(result, ".", entry)
            elif isinstance(entry, (list, tuple)):
                prev_result = result = Breakable(
                    start="$$HREPR.ucall(",
                    body=join(
                        [
                            prev_result,
                            recurse(last_symbol),
                            *[recurse(x) for x in entry],
                        ],
                        sep=",",
                    ),
                    end=")",
                )
            elif isinstance(entry, CodeWrapper):
                prev_result = result = entry(result)
            else:  # pragma: no cover
                raise TypeError(f"Cannot process {type(entry).__name__}.")

        return result

    def js_embed(self, ret: Returns):
        self.script_accumulator.returns = ret.value
        return Text("$$INTO")

    def js_embed(self, res: resource.Resource):
        return recurse(res.obj)

    def js_embed(self, x: object):
        if hasattr(x, "__js_embed__"):
            return x.__js_embed__(self)
        else:
            raise TypeError(
                f"Resources of type {type(x).__name__} cannot be serialized to JavaScript."
            )


class HTMLGenerator:
    def __init__(self, block_generator_class=BlockGenerator, hrepr=None):
        self.seen_resources = set()
        self.block_generator_class = block_generator_class
        self.hrepr = hrepr

    def block(self):
        return self.block_generator_class(
            global_generator=self, hrepr=self.hrepr
        )

    def blockgen(self, node, *, seen_resources=None, process_extra=True):
        blk = self.block()
        blk.result = blk.node_embed(node)

        if process_extra:
            blk.processed_extra = proc = []
            while blk.extra:
                nxt = blk.extra.popleft()
                proc.append(blk.node_embed(nxt))

        if seen_resources is not True:
            seen = (
                self.seen_resources
                if seen_resources is None
                else seen_resources
            )
            blk.processed_resources = proc = []
            while blk.resources:
                nxt = blk.resources.popleft()
                if nxt not in seen:
                    proc.append(blk.node_embed(nxt))
                    seen.add(nxt)

        return blk

    def to_string(self, node):
        return str(self.blockgen(node, seen_resources=True).result)

    def to_jupyter(self, node):  # pragma: no cover
        blk = self.blockgen(node, seen_resources=set())
        elem = H.div(
            css_nbreset,
            blk.processed_resources,
            H.div["hrepr"](blk.result, blk.processed_extra),
        )
        return self.to_string(elem)

    def as_page(self, node):
        """
        Wrap this Tag as a self-contained webpage. Create a page with
        the following structure:

        .. code-block:: html

            <!DOCTYPE html>
            <html>
              <head>
                <meta http-equiv="Content-type"
                      content="text/html"
                      charset="UTF-8" />
                {self.resources}
              </head>
              <body>
                {self}
              </body>
            </html>
        """
        blk = self.blockgen(node, seen_resources=set())
        utf8 = H.meta(
            {"http-equiv": "Content-type"}, content="text/html", charset="UTF-8"
        )
        page = H.inline(
            H.raw("<!DOCTYPE html>"),
            H.html(
                H.head(utf8, blk.processed_resources),
                H.body(blk.result, blk.processed_extra),
            ),
        )
        return self.to_string(page)

    def __call__(self, node):
        blk = self.blockgen(node)
        return self.to_string(H.inline(blk.result, blk.processed_extra))


standard_html = HTMLGenerator()
