import logging
import os
import sys
import unittest
from abc import ABC

from pydantic import HttpUrl
from pydantic_settings import BaseSettings, SettingsConfigDict

from python_di.di_container import DIContainer, Dependency, DependencyInstance


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

        class ConcreteA:
            def __init__(self, b: AbstractClass):
                self._b = b

        class B(AbstractClass):
            pass

        container = DIContainer()
        container.register_dependencies(
            dependencies_types_with_kwargs=[Dependency(B), Dependency(ConcreteA)]
        )
        concrete_a = container[ConcreteA]
        self.assertIsInstance(concrete_a._b, B)

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
            test_setting: HttpUrl = HttpUrl("http://www.test.de")

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
        os.environ.clear()
