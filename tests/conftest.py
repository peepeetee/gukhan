# SPDX-License-Identifier: Apache-2.0
import pytest


def pytest_configure(config):
    config.addinivalue_line("markers", "kiwi: needs the real Kiwi model (kiwipiepy)")


def pytest_collection_modifyitems(config, items):
    try:
        import kiwipiepy  # noqa: F401
    except ImportError:
        skip = pytest.mark.skip(reason="kiwipiepy not installed")
        for item in items:
            if "kiwi" in item.keywords:
                item.add_marker(skip)
