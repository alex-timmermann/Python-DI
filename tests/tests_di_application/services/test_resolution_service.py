import logging
import os
import sys
import unittest
from abc import ABC

from pydantic import HttpUrl
from pydantic_settings import BaseSettings, SettingsConfigDict

from python_di_application.dependency import Dependency
from python_di_application.instance_cache import InstanceCache
from python_di_application.services.registry_service import RegistryService
from python_di_application.services.resolution_service import ResolutionService


class TestResolutionService(unittest.TestCase):
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

    def test_resolve_dependency_caches_singleton(self) -> None:
        class A:
            pass

        self.registry.upsert_dependency(dependency=Dependency(dependency_type=A))

        first = self.resolution.resolve_dependency(dependency_type=A)
        second = self.resolution.resolve_dependency(dependency_type=A)

        self.assertIs(first, second)
        self.assertIs(self.cache[A], first)
        self.assertTrue(self.cache.was_dependency_used(dependency_type=A))

    def test_find_dependency_in_registry_rejects_direct_abstract_registration(
        self,
    ) -> None:
        class AbstractService(ABC):
            pass

        self.registry.upsert_dependency(
            dependency=Dependency(dependency_type=AbstractService)
        )

        with self.assertRaises(TypeError) as exc:
            self.resolution.find_dependency_in_registry(dependency_type=AbstractService)

        self.assertIn(
            "abstract dependencies need be to overwritten", exc.exception.args[0]
        )

    def test_resolve_dependency_uses_constructor_kwargs_and_defaults(self) -> None:
        class Service:
            def __init__(self, value: str, amount: int = 3) -> None:
                self.value = value
                self.amount = amount

        self.registry.upsert_dependency(
            dependency=Dependency(dependency_type=Service, value="configured")
        )

        service = self.resolution.resolve_dependency(dependency_type=Service)

        self.assertEqual(service.value, "configured")
        self.assertEqual(service.amount, 3)

    def test_resolve_dependency_for_base_settings_uses_env_values(self) -> None:
        class ConfigBase(BaseSettings):
            model_config = SettingsConfigDict(env_prefix="TEST_")

        class Settings(ConfigBase):
            endpoint: HttpUrl

        os.environ["TEST_ENDPOINT"] = "https://example.test"
        self.registry.upsert_dependency(dependency=Dependency(dependency_type=Settings))
        try:
            settings = self.resolution.resolve_dependency(dependency_type=Settings)
        finally:
            os.environ.pop("TEST_ENDPOINT", None)

        self.assertEqual(str(settings.endpoint), "https://example.test/")

    def test_resolve_dependency_raises_for_missing_annotation(self) -> None:
        class Service:
            def __init__(self, missing) -> None:
                self.missing = missing

        self.registry.upsert_dependency(dependency=Dependency(dependency_type=Service))

        with self.assertRaises(ValueError) as exc:
            self.resolution.resolve_dependency(dependency_type=Service)

        self.assertIn("Missing type annotation", exc.exception.args[0])

    def test_resolve_dependency_uses_abstract_contract_match(self) -> None:
        class AbstractService(ABC):
            pass

        class Service(AbstractService):
            pass

        class Consumer:
            def __init__(self, dependency: AbstractService) -> None:
                self.dependency = dependency

        self.registry.register_dependencies(
            dependencies_types_with_kwargs=[
                Dependency(dependency_type=Service),
                Dependency(dependency_type=Consumer),
            ]
        )

        consumer = self.resolution.resolve_dependency(dependency_type=Consumer)

        self.assertIsInstance(consumer.dependency, Service)
