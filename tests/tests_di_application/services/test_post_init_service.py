import logging
import sys
import unittest

from python_di_application.dependency import Dependency
from python_di_application.di_container import DIContainer
from python_di_application.instance_cache import InstanceCache
from python_di_application.services.post_init_service import PostInitService
from python_di_application.services.registry_service import RegistryService
from python_di_application.services.resolution_service import ResolutionService


class WrapperService:
    def wrap(self, func):
        def wrapped():
            return f"wrapped:{func()}"

        return wrapped


class WrappedService:
    @DIContainer.post_init_wrap(WrapperService.wrap)
    def value(self) -> str:
        return "raw"


class TestPostInitService(unittest.TestCase):
    def setUp(self) -> None:
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s %(levelname)s %(name)s %(message)s",
            stream=sys.stdout,
            force=True,
        )
        self.registry = RegistryService()
        self.cache = InstanceCache()
        self.resolution = ResolutionService(
            registry_service=self.registry,
            instance_cache=self.cache,
        )
        self.post_init_service = PostInitService(
            resolution_service=self.resolution,
            instance_cache=self.cache,
        )

    def test_apply_post_init_wrappers_wraps_registered_singletons(self) -> None:
        self.registry.register_dependencies(
            dependencies_types_with_kwargs=[
                Dependency(dependency_type=WrapperService),
                Dependency(dependency_type=WrappedService),
            ]
        )
        wrapped_service = self.resolution.resolve_dependency(
            dependency_type=WrappedService
        )
        _ = self.resolution.resolve_dependency(dependency_type=WrapperService)

        self.post_init_service.apply_post_init_wrappers()

        self.assertEqual(wrapped_service.value(), "wrapped:raw")
