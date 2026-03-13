import logging
import os
import sys
import unittest
from abc import ABC
from unittest.mock import MagicMock

from pydantic import HttpUrl
from pydantic_settings import BaseSettings, SettingsConfigDict

from python_di_application.dependency import DependencyInstance, Dependency
from python_di_application.di_container import DIContainer
from python_di_application.test_di_container import TestDIContainer


class PostInitWrapper:
    def wrap(self, func):
        def wrapped():
            return f"wrapped:{func()}"

        return wrapped


class PostInitTestClass:
    @DIContainer.post_init_wrap(PostInitWrapper.wrap)
    def value(self) -> str:
        return "raw"


class TestDependencyContainer(unittest.TestCase):
    def setUp(self) -> None:
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s %(levelname)s %(name)s %(message)s",
            stream=sys.stdout,
            force=True,
        )

    def test_dependency_override_abstract_class(self) -> None:
        class AbstractTest(ABC):
            pass

        class ConcreteType(AbstractTest):
            pass

        container = DIContainer()
        container.register_dependency(
            dependency=Dependency(dependency_type=AbstractTest)
        )

        container.override_dependency(
            dependency=Dependency(dependency_type=ConcreteType)
        )

        concrete_type = container[ConcreteType]

        container.check_if_all_dependencies_are_used()

        self.assertIsInstance(concrete_type, ConcreteType)

    def test_dependency_override_concrete_instance(self) -> None:
        class AbstractTest(ABC):
            pass

        class ConcreteType(AbstractTest):
            pass

        container = DIContainer()
        container.register_dependency(
            dependency=Dependency(dependency_type=AbstractTest)
        )

        concrete_instance = ConcreteType()

        container.replace_dependency_instance(
            dependency_instance=DependencyInstance(instance_obj=concrete_instance)
        )
        container.check_if_all_dependencies_are_used()
        self.assertEqual(concrete_instance, container[ConcreteType])

    def test_3_level_deep(self) -> None:
        class A:
            pass

        class B:
            def __init__(self, a: A) -> None:
                self._a = a

        class C:
            def __init__(self, b: B) -> None:
                self._b = b

        container = DIContainer()
        container.register_dependencies(
            dependencies_types_with_kwargs=[Dependency(A), Dependency(B), Dependency(C)]
        )
        c = container[C]
        container.check_if_all_dependencies_are_used()
        self.assertIsInstance(c._b._a, A)

    def test_unused_raises(self) -> None:
        class A:
            pass

        class B:
            def __init__(self, a: A) -> None:
                self._a = a

        class C:
            def __init__(self, b: B) -> None:
                self._b = b

        class D:
            pass

        container = DIContainer()
        container.register_dependencies(
            dependencies_types_with_kwargs=[
                Dependency(A),
                Dependency(B),
                Dependency(C),
                Dependency(D),
            ]
        )

        _ = container[C]
        with self.assertRaises(ValueError) as e:
            container.check_if_all_dependencies_are_used()
        self.assertIn("not used", e.exception.args[0])

    def test_empty_signature(self) -> None:
        class A:
            pass

        container = DIContainer()

        container.register_dependency(dependency=Dependency(A))

        a = container[A]

        self.assertIsInstance(a, A)

    def test_double_injection_should_fail(self) -> None:
        class AbstractTest(ABC):
            pass

        class ConcreteType(AbstractTest):
            pass

        class ConcreteType2(AbstractTest):
            pass

        class C:
            def __init__(self, c: AbstractTest) -> None:
                self._c = c

        container = DIContainer()
        container.register_dependencies(
            dependencies_types_with_kwargs=[
                Dependency(ConcreteType),
                Dependency(ConcreteType2),
                Dependency(C),
            ]
        )

        with self.assertRaises(ValueError) as e:
            _ = container[C]
        self.assertIn("Ambiguous result multiple", e.exception.args[0])

    def test_abstract_instantiation_should_fail(self) -> None:
        class AbstractTest(ABC):
            pass

        class C:
            def __init__(self, c: AbstractTest) -> None:
                self._c = c

        container = DIContainer()
        container.register_dependencies(
            dependencies_types_with_kwargs=[Dependency(AbstractTest), Dependency(C)]
        )

        with self.assertRaises(TypeError) as e:
            _ = container[C]
        self.assertIn(
            "abstract dependencies need be to overwritten", e.exception.args[0]
        )

    def test_abstract_injected_class_success(self) -> None:
        class AbstractClass(ABC):
            pass

        class A:
            def __init__(self, b: AbstractClass):
                self._b = b

        class ConcreteB(AbstractClass):
            pass

        container = DIContainer()
        container.register_dependencies(
            dependencies_types_with_kwargs=[Dependency(ConcreteB), Dependency(A)]
        )
        concrete_a = container[A]
        self.assertIsInstance(concrete_a._b, ConcreteB)

    def test_base_settings_injection_with_default(self) -> None:
        class TestSettings(BaseSettings):
            test_setting: str = "test"

        class B:
            def __init__(self, settings: TestSettings):
                self._settings = settings

        container = DIContainer()
        container.register_dependencies(
            dependencies_types_with_kwargs=[Dependency(TestSettings), Dependency(B)]
        )
        b = container[B]
        self.assertEqual(b._settings.test_setting, "test")

    def test_base_settings_injection_without_and_override(self) -> None:
        override_http = HttpUrl("https://override.de")

        class TestSettings(BaseSettings):
            test_setting: HttpUrl = HttpUrl("http://www.test.de")  # NOSONAR

        class B:
            def __init__(self, settings: TestSettings):
                self._settings = settings

        container = DIContainer()
        container.register_dependencies(
            dependencies_types_with_kwargs=[Dependency(TestSettings), Dependency(B)]
        )
        container.replace_dependency_instances(
            dependency_instances=[
                DependencyInstance(
                    instance_obj=TestSettings(test_setting=override_http)
                ),
            ]
        )
        b = container[B]
        self.assertEqual(b._settings.test_setting, override_http)

    def test_base_settings_injection_with_env_var(self) -> None:
        override_http = HttpUrl("https://override.de")

        class ConfigBase(BaseSettings):
            model_config = SettingsConfigDict(env_prefix="TEST_")

        class TestSettings(ConfigBase):
            test_setting: HttpUrl

        class B:
            def __init__(self, settings: TestSettings):
                self._settings = settings

        os.environ["TEST_TEST_SETTING"] = override_http.unicode_string()
        container = DIContainer()
        container.register_dependencies(
            dependencies_types_with_kwargs=[Dependency(TestSettings), Dependency(B)]
        )
        b = container[B]
        self.assertEqual(b._settings.test_setting, override_http)
        os.environ.pop("TEST_TEST_SETTING", None)

    def test_resolve_dependency_returns_singleton_instance(self) -> None:
        class A:
            pass

        container = DIContainer()
        container.register_dependency(Dependency(A))

        first = container[A]
        second = container.resolve_dependency(A)

        self.assertIs(first, second)

    def test_reinitialize_dependency_replaces_cached_singleton(self) -> None:
        class A:
            pass

        container = DIContainer()
        container.register_dependency(Dependency(A))

        first = container[A]
        second = container.reinitialize_dependency(A)

        self.assertIsNot(first, second)
        self.assertIs(second, container[A])

    def test_override_unknown_dependency_raises(self) -> None:
        class A:
            pass

        container = DIContainer()

        with self.assertRaises(ValueError) as exc:
            container.override_dependency(Dependency(A))

        self.assertIn("überschrieben", exc.exception.args[0])

    def test_replace_unknown_dependency_instance_raises(self) -> None:
        class A:
            pass

        container = DIContainer()

        with self.assertRaises(TypeError) as exc:
            container.replace_dependency_instance(DependencyInstance(A()))

        self.assertIn("cannot be replaced", exc.exception.args[0])

    def test_dependency_kwargs_override_constructor_arguments(self) -> None:
        class A:
            def __init__(self, value: str, amount: int = 3) -> None:
                self.value = value
                self.amount = amount

        container = DIContainer()
        container.register_dependency(Dependency(A, value="configured"))

        instance = container[A]

        self.assertEqual(instance.value, "configured")
        self.assertEqual(instance.amount, 3)

    def test_missing_annotation_raises(self) -> None:
        class A:
            def __init__(self, value) -> None:
                self.value = value

        container = DIContainer()
        container.register_dependency(Dependency(A))

        with self.assertRaises(ValueError) as exc:
            _ = container[A]

        self.assertIn("Missing type annotation", exc.exception.args[0])

    def test_create_test_instance_injects_mock_for_missing_dependency(self) -> None:
        class Collaborator:
            def call(self) -> str:
                return "value"

        class Service:
            def __init__(self, collaborator: Collaborator) -> None:
                self.collaborator = collaborator

        container = TestDIContainer()

        service = container.create_test_instance(dependency_type=Service)

        self.assertIsInstance(service, Service)
        self.assertIsInstance(service.collaborator, MagicMock)
        self.assertIs(service, container[Service])

    def test_post_init_wrap_applies_wrapper(self) -> None:
        container = DIContainer()
        container.register_dependencies(
            [Dependency(PostInitWrapper), Dependency(PostInitTestClass)]
        )

        service = container[PostInitTestClass]
        _ = container[PostInitWrapper]
        container.apply_post_init_wrappers()

        self.assertEqual(service.value(), "wrapped:raw")

    def test_registered_base_type_is_not_used_for_subclass_request(self) -> None:
        class Base:
            pass

        class Child(Base):
            pass

        container = DIContainer()
        container.register_dependency(Dependency(Base))

        with self.assertRaises(ValueError) as exc:
            _ = container[Child]

        self.assertIn("not found in registry", exc.exception.args[0])

    def test_unregistered_base_settings_type_is_not_resolved_from_another(self) -> None:
        class PrimarySettings(BaseSettings):
            api_url: str = "https://primary.test"

        class SecondarySettings(BaseSettings):
            api_url: str = "https://secondary.test"

        container = DIContainer()
        container.register_dependency(Dependency(PrimarySettings))

        with self.assertRaises(ValueError) as exc:
            _ = container[SecondarySettings]

        self.assertIn("not found in registry", exc.exception.args[0])
