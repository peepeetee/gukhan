# SPDX-License-Identifier: Apache-2.0
"""The public API is what ``__all__`` says, it is typed, and it is documented (docs/api-policy.md)."""

import importlib
import importlib.resources
import inspect
import re
from pathlib import Path

import pytest

import gukhan

ROOT = Path(__file__).resolve().parent.parent
MODULES = ["convert", "lexicon", "overrides", "analyser", "report", "review", "suggest", "formats"]


def test_top_level_names_exist() -> None:
    assert sorted(gukhan.__all__) == sorted(set(gukhan.__all__))
    for name in gukhan.__all__:
        assert hasattr(gukhan, name), name


def test_package_does_not_shadow_its_modules() -> None:
    # `from gukhan.convert import convert` is fine, but `gukhan.convert` must stay the module.
    assert inspect.ismodule(gukhan.convert)
    assert callable(gukhan.convert.convert)


@pytest.mark.parametrize("module", MODULES)
def test_module_all_names_exist_and_are_documented(module: str) -> None:
    mod = importlib.import_module(f"gukhan.{module}")
    assert mod.__all__, module
    for name in mod.__all__:
        obj = getattr(mod, name)
        if inspect.isclass(obj) or inspect.isfunction(obj):
            doc = inspect.getdoc(obj) or ""
            # a dataclass without a docstring gets "Name(field, ...)" from the standard library
            assert doc and not doc.startswith(f"{name}("), f"gukhan.{module}.{name} has no docstring"


def test_public_names_are_in_the_api_reference() -> None:
    text = (ROOT / "docs" / "api.md").read_text(encoding="utf-8")
    for name in gukhan.__all__:
        if name != "__version__":
            assert re.search(rf"gukhan\.{name}\b", text), f"{name} missing from docs/api.md"


def test_py_typed_marker_ships() -> None:
    assert importlib.resources.files("gukhan").joinpath("py.typed").is_file()
    assert '"py.typed"' in (ROOT / "pyproject.toml").read_text(encoding="utf-8")
