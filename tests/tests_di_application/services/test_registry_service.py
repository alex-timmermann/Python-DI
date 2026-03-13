import logging
import sys
import unittest
from abc import ABC

from python_di_application.dependency import Dependency, DependencyInstance
from python_di_application.services.registry_service import RegistryService


class TestRegistryService(unittest.TestCase):
    def setUp(self) -> None:
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s %(levelname)s %(name)s %(message)s",
            stream=sys.stdout,
            force=True,
        )
        self.registry = RegistryService()

    def test_register_instance_adds_singleton_and_dependency(self) -> None:
        class A:
            pass

        instance = A()

        self.registry.register_instance(instance_obj=instance)

        dependency = self.registry.get_direct_dependency(dependency_type=A)
        self.assertIsNotNone(dependency)
        assert dependency is not None
        self.assertIs(dependency.dependency_type, A)
        self.assertIs(dependency.dependency_interface, A)

    def test_find_registered_dependency_by_exact_concrete_type(self) -> None:
        class Interface:
            pass

        class Implementation(Interface):
            pass

        self.registry.upsert_dependency(
            dependency=Dependency(
                dependency_type=Implementation,
                dependency_interface=Interface,
            )
        )

        dependency = self.registry.find_registered_dependency(
            dependency_type=Implementation
        )

        self.assertIsNotNone(dependency)
        assert dependency is not None
        self.assertIs(dependency.dependency_interface, Interface)
        self.assertIs(dependency.dependency_type, Implementation)

    def test_find_registered_dependency_by_abstract_contract(self) -> None:
        class AbstractService(ABC):
            pass

        class Service(AbstractService):
            pass

        self.registry.upsert_dependency(dependency=Dependency(dependency_type=Service))

        dependency = self.registry.find_registered_dependency(
            dependency_type=AbstractService
        )

        self.assertIsNotNone(dependency)
        assert dependency is not None
        self.assertIs(dependency.dependency_interface, Service)

    def test_find_registered_dependency_does_not_fall_back_for_concrete_subclass(
        self,
    ) -> None:
        class Base:
            pass

        class Child(Base):
            pass

        self.registry.upsert_dependency(dependency=Dependency(dependency_type=Base))

        dependency = self.registry.find_registered_dependency(dependency_type=Child)

        self.assertIsNone(dependency)

    def test_find_registered_dependency_raises_for_ambiguous_contract(self) -> None:
        class AbstractService(ABC):
            pass

        class ServiceA(AbstractService):
            pass

        class ServiceB(AbstractService):
            pass

        self.registry.register_dependencies(
            dependencies_types_with_kwargs=[
                Dependency(dependency_type=ServiceA),
                Dependency(dependency_type=ServiceB),
            ]
        )

        with self.assertRaises(ValueError) as exc:
            self.registry.find_registered_dependency(dependency_type=AbstractService)

        self.assertIn("Ambiguous result multiple", exc.exception.args[0])

    def test_override_dependency_reuses_registered_interface(self) -> None:
        class AbstractService(ABC):
            pass

        class OldService(AbstractService):
            pass

        class NewService(AbstractService):
            pass

        self.registry.upsert_dependency(
            dependency=Dependency(dependency_type=AbstractService)
        )
        self.registry.upsert_dependency(Dependency(dependency_type=OldService))

        self.registry.override_dependency(
            dependency=Dependency(
                dependency_type=NewService,
                ignore_unused=True,
                value="configured",
            )
        )

        dependency = self.registry.get_direct_dependency(
            dependency_type=AbstractService
        )
        assert dependency is not None
        self.assertIs(dependency.dependency_interface, AbstractService)
        self.assertIs(dependency.dependency_type, NewService)
        self.assertTrue(dependency.ignore_unused)
        self.assertEqual(dependency.kwargs["value"], "configured")

    def test_replace_dependency_instance_updates_dependency_type(self) -> None:
        class AbstractService(ABC):
            pass

        class Service(AbstractService):
            pass

        instance = Service()
        self.registry.upsert_dependency(
            dependency=Dependency(dependency_type=AbstractService)
        )

        replacement_dependency = self.registry.replace_dependency_instance(
            dependency_instance=DependencyInstance(instance_obj=instance)
        )

        self.assertIs(replacement_dependency.dependency_interface, AbstractService)
        self.assertIs(replacement_dependency.dependency_type, Service)
        dependency = self.registry.find_registered_dependency(dependency_type=Service)
        self.assertIsNotNone(dependency)
        assert dependency is not None
        self.assertIs(dependency.dependency_interface, AbstractService)
        self.assertIs(dependency.dependency_type, Service)

    def test_find_registered_dependency_for_update_matches_registered_base_interface(
        self,
    ) -> None:
        class AbstractService(ABC):
            pass

        class Service(AbstractService):
            pass

        self.registry.upsert_dependency(
            dependency=Dependency(dependency_type=AbstractService)
        )

        dependency = self.registry.find_registered_dependency_for_update(
            dependency_type=Service
        )

        self.assertIsNotNone(dependency)
        assert dependency is not None
        self.assertIs(dependency.dependency_interface, AbstractService)

    def test_get_registered_dependencies_returns_registered_values(self) -> None:
        class A:
            pass

        class B:
            pass

        self.registry.register_dependencies(
            dependencies_types_with_kwargs=[
                Dependency(dependency_type=A),
                Dependency(dependency_type=B),
            ]
        )

        registered_dependencies = self.registry.get_registered_dependencies()

        self.assertEqual(len(tuple(registered_dependencies)), 2)
