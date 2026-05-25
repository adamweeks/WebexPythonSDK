"""Unit tests for GeneratorContainer limit and pagination behavior.

These tests do not require a Webex API token and run without network access.
"""

import importlib.util
import os

import pytest

spec = importlib.util.spec_from_file_location(
    "generator_containers",
    os.path.join(os.path.dirname(__file__), '..', 'src', 'webexpythonsdk', 'generator_containers.py'),
)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)
GeneratorContainer = mod.GeneratorContainer
generator_container = mod.generator_container


def _paginated_source(total_items, max=None, limit=None):
    """Simulate an API list() generator: yields total_items items.
    max is a page-size hint (ignored here since it's a mock).
    limit is captured by GeneratorContainer.__iter__ and never reaches here.
    """
    for i in range(total_items):
        yield i


@generator_container
def _api_list(max=None, limit=None):
    """Simulates a @generator_container-decorated API list method."""
    for i in range(100):
        yield i


class TestLimitParameter:
    """limit= caps the total number of items returned across all pages."""

    def test_limit_caps_total_items(self):
        gc = GeneratorContainer(_paginated_source, total_items=20, limit=5)
        assert list(gc) == list(range(5))

    def test_no_limit_returns_all_items(self):
        gc = GeneratorContainer(_paginated_source, total_items=10)
        assert list(gc) == list(range(10))

    def test_limit_none_explicit_returns_all(self):
        gc = GeneratorContainer(_paginated_source, total_items=10, limit=None)
        assert list(gc) == list(range(10))

    def test_limit_larger_than_available_returns_all(self):
        gc = GeneratorContainer(_paginated_source, total_items=5, limit=100)
        assert list(gc) == list(range(5))

    def test_limit_zero_returns_nothing(self):
        gc = GeneratorContainer(_paginated_source, total_items=10, limit=0)
        assert list(gc) == []

    def test_limit_is_reusable(self):
        """GeneratorContainer with limit must be safely reusable."""
        gc = GeneratorContainer(_paginated_source, total_items=20, limit=3)
        assert list(gc) == list(gc) == [0, 1, 2]

    def test_decorator_with_limit(self):
        assert len(list(_api_list(limit=5))) == 5

    def test_decorator_without_limit_returns_all(self):
        assert len(list(_api_list())) == 100


class TestMaxParameter:
    """max= is a page-size hint only; it does NOT cap total items returned."""

    def test_max_does_not_cap_total_items(self):
        """max controls page size, not total results — all items are returned."""
        gc = GeneratorContainer(_paginated_source, total_items=20, max=5)
        # max=5 is a page-size hint; all 20 items should still be yielded
        assert len(list(gc)) == 20

    def test_max_and_limit_together(self):
        """max sets page size, limit caps the total."""
        gc = GeneratorContainer(_paginated_source, total_items=50, max=10, limit=15)
        assert list(gc) == list(range(15))


class TestEarlyTermination:
    """Breaking out of a for loop stops pagination immediately."""

    def test_break_stops_at_found_item(self):
        """Simulates searching through spaces and stopping once found."""
        gc = GeneratorContainer(_paginated_source, total_items=100)
        visited = []
        for item in gc:
            visited.append(item)
            if item == 4:  # found what we were looking for
                break
        assert visited == [0, 1, 2, 3, 4]

    def test_slice_notation(self):
        gc = GeneratorContainer(_paginated_source, total_items=20)
        assert list(gc[0:5]) == list(range(5))
