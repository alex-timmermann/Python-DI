from abc import ABC
import inspect
import logging
from collections.abc import Iterable
from typing import Any

from python_di_application.dependency import Dependency, DependencyInstance

logger = logging.getLogger(__name__)


class RegistryService:
    def __init__(self) -> None:
        self._registry: dict[type, Dependency] = {}

    def register_instance[T](
        self, instance_obj: T, interface_type: type | None = None
    ) -> None:
        instance_type = interface_type if interface_type else type(instance_obj)
        if instance_type not in self._registry:
            self.upsert_dependency(
                dependency=Dependency(
                    dependency_type=type(instance_obj),
                    dependency_interface=instance_type,
                )
            )

    def register_instances(self, instances: list[DependencyInstance]) -> None:
        for instance in instances:
            self.register_instance(
                instance_obj=instance.instance_obj,
                interface_type=instance.dependency_interface,
            )

    def upsert_dependency(self, dependency: Dependency) -> None:
        self._registry[dependency.dependency_interface] = dependency

    def register_dependencies(
        self, dependencies_types_with_kwargs: list[Dependency[Any]]
    ) -> None:
        for dependency in dependencies_types_with_kwargs:
            self.upsert_dependency(dependency=dependency)

    def override_dependencies(
        self, dependencies_types_with_kwargs: list[Dependency[Any]]
    ) -> None:
        for dependency in dependencies_types_with_kwargs:
            self.override_dependency(dependency=dependency)

    def override_dependency(self, dependency: Dependency) -> None:
        reg_dependency = self._registry.get(dependency.dependency_interface)
        if not reg_dependency:
            reg_dependency = self.find_registered_dependency_for_update(
                dependency_type=dependency.dependency_type
            )

        logger.debug(
            msg=f"Found dependency {reg_dependency} which will be overridden with {dependency}"
        )
        if reg_dependency:
            self.upsert_dependency(
                dependency=Dependency(
                    dependency_type=dependency.dependency_type,
                    dependency_interface=reg_dependency.dependency_interface,
                    ignore_unused=dependency.ignore_unused,
                    **dependency.kwargs,
                )
            )
            return

        raise ValueError(
            f"Dependency {dependency.dependency_interface} konnte nicht im Registry gefunden oder überschrieben werden."
        )

    def replace_dependency_instance(
        self, dependency_instance: DependencyInstance
    ) -> Dependency:
        reg_dependency = self._registry.get(dependency_instance.dependency_interface)
        if not reg_dependency:
            reg_dependency = self.find_registered_dependency_for_update(
                dependency_type=dependency_instance.dependency_interface
            )
        logger.debug(
            msg=f"Found dependency {reg_dependency} which will be replaced with instance"
            f" of type: {type(dependency_instance.instance_obj).__name__}"
        )
        if not reg_dependency:
            raise TypeError(
                f"Dependency {reg_dependency} not in registry, cannot be replaced with instance"
            )

        replacement_dependency = Dependency(
            dependency_type=type(dependency_instance.instance_obj),
            dependency_interface=reg_dependency.dependency_interface,
            ignore_unused=reg_dependency.ignore_unused,
            **reg_dependency.kwargs,
        )
        self.upsert_dependency(dependency=replacement_dependency)
        return replacement_dependency

    def get_registered_dependencies(self) -> Iterable[Dependency]:
        return list(self._registry.values())

    def check_if_dependency_is_registered(self, dependency_type: type) -> bool:
        return dependency_type in self._registry

    def get_direct_dependency[T](self, dependency_type: type[T]) -> Dependency | None:
        return self._registry.get(dependency_type)

    def find_registered_dependency[T](
        self, dependency_type: type[T]
    ) -> Dependency | None:
        dependency = self.get_direct_dependency(dependency_type=dependency_type)
        if dependency:
            return dependency

        dependency = self._find_dependency_by_exact_type(
            dependency_type=dependency_type
        )
        if dependency:
            return dependency

        if not self._is_non_concrete_contract(dependency_type):
            return None

        return self._find_dependency_by_subclass_of_registered_deps(
            dependency_type=dependency_type
        )

    def find_registered_dependency_for_update[T](
        self, dependency_type: type[T]
    ) -> Dependency | None:
        dependency = self.find_registered_dependency(dependency_type=dependency_type)
        if dependency:
            return dependency

        matching_dependencies = [
            dependency
            for dependency in self._registry.values()
            if dependency.dependency_interface in inspect.getmro(dependency_type)
        ]
        if len(matching_dependencies) > 1:
            raise ValueError(
                f"Ambiguous result multiple registered base interfaces of {dependency_type} found"
            )
        if len(matching_dependencies) == 1:
            return matching_dependencies[0]
        return None

    def _find_dependency_by_exact_type[T](
        self, dependency_type: type[T]
    ) -> Dependency | None:
        matching_dependencies = [
            dependency
            for dependency in self._registry.values()
            if dependency.dependency_type is dependency_type
        ]
        if len(matching_dependencies) > 1:
            raise ValueError(f"Concrete type {dependency_type} is already registered")
        if len(matching_dependencies) == 1:
            return matching_dependencies[0]
        return None

    def _find_dependency_by_subclass_of_registered_deps[T](
        self, dependency_type: type[T]
    ) -> Dependency | None:
        matching_dependencies = [
            dependency
            for dependency in self._registry.values()
            if dependency_type in inspect.getmro(dependency.dependency_interface)
        ]
        if len(matching_dependencies) > 1:
            raise ValueError(
                f"Ambiguous result multiple registered subclasses of {dependency_type} found"
            )
        if len(matching_dependencies) == 1:
            dependency = matching_dependencies[0]
            logger.debug(
                msg=f"Found subclass {dependency.dependency_interface} in registry for type {dependency_type}"
            )
            return dependency
        return None

    @staticmethod
    def _is_non_concrete_contract(dependency_type: type) -> bool:
        return inspect.isabstract(dependency_type) or (
            len(dependency_type.mro()) > 1 and dependency_type.mro()[1] is ABC
        )
