import logging
import sys
import unittest

from python_di_application.instance_cache import InstanceCache


class TestInstanceCache(unittest.TestCase):
    def setUp(self) -> None:
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s %(levelname)s %(name)s %(message)s",
            stream=sys.stdout,
            force=True,
        )
        self.cache = InstanceCache()

    def test_store_and_get_singleton(self) -> None:
        class A:
            pass

        instance = A()

        self.cache.store_singleton(dependency_type=A, instance_obj=instance)

        self.assertIs(self.cache[A], instance)

    def test_delete_singleton_removes_cached_instance(self) -> None:
        class A:
            pass

        self.cache.store_singleton(dependency_type=A, instance_obj=A())

        self.cache.delete_singleton(dependency_type=A)

        self.assertIsNone(self.cache[A])

    def test_mark_dependency_as_used_tracks_usage(self) -> None:
        class A:
            pass

        self.cache.mark_dependency_as_used(dependency_type=A)

        self.assertTrue(self.cache.was_dependency_used(dependency_type=A))
