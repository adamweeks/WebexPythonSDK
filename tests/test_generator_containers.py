"""Unit tests for GeneratorContainer, specifically the max/limit behavior.

These tests do not require a Webex API token and run without network access.
"""

import importlib.util
import os

import pytest
from itertools import islice

import importlib.util
spec = importlib.util.spec_from_file_location(
    "generator_containers",
    os.path.join(os.path.dirname(__file__), '..', 'src', 'webexpythonsdk', 'generator_containers.py'),
)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)
GeneratorContainer = mod.GeneratorContainer
generator_container = mod.generator_container


def make_paginated_generator(total_items, max=None):
    """Simulate a paginated list generator that yields `total_items` items."""
    for i in range(total_items):
        yield i


@generator_container
def list_with_max(max=None):
    """Simulates an API list() method that accepts a max parameter."""
    for i in range(100):
        yield i


class TestGeneratorContainerMaxLimit:
    """Tests that max parameter limits total items returned."""

    def test_no_max_returns_all_items(self):
        """Without max, all items are returned via auto-pagination."""
        gc = GeneratorContainer(make_paginated_generator, total_items=10)
        assert list(gc) == list(range(10))

    def test_max_limits_total_items(self):
        """max=N must cap the total items yielded, not just the page size."""
        gc = GeneratorContainer(make_paginated_generator, total_items=20, max=5)
        result = list(gc)
        # This was the bug: before the fix, all 20 items were returned
        assert len(result) == 5
        assert result == list(range(5))

    def test_max_none_explicit_returns_all(self):
        """Explicitly passing max=None means no limit."""
        gc = GeneratorContainer(make_paginated_generator, total_items=10, max=None)
        assert len(list(gc)) == 10

    def test_max_larger_than_available_returns_all(self):
        """max larger than available items returns only what exists."""
        gc = GeneratorContainer(make_paginated_generator, total_items=5, max=100)
        assert len(list(gc)) == 5

    def test_max_is_reusable(self):
        """GeneratorContainer with max should be safely reusable."""
        gc = GeneratorContainer(make_paginated_generator, total_items=20, max=3)
        first = list(gc)
        second = list(gc)
        assert first == second == [0, 1, 2]

    def test_max_zero_returns_nothing(self):
        """max=0 yields nothing without error."""
        gc = GeneratorContainer(make_paginated_generator, total_items=10, max=0)
        assert list(gc) == []

    def test_decorator_with_max(self):
        """@generator_container decorated functions respect max via __iter__."""
        # Without max: gets all 100 items
        gc_all = list_with_max()
        assert len(list(gc_all)) == 100

        # With max=5: gets only 5 items
        gc_limited = list_with_max(max=5)
        assert len(list(gc_limited)) == 5

    def test_slice_still_works_with_max(self):
        """Slicing a GeneratorContainer still works correctly."""
        gc = GeneratorContainer(make_paginated_generator, total_items=20, max=10)
        # Slice should use islice and its own stop value
        result = list(gc[0:3])
        assert result == [0, 1, 2]
