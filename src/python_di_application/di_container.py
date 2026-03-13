import functools
from collections.abc import Callable
from typing import Any, ParamSpec, TypeVar

from python_di_application.dependency import Dependency, DependencyInstance
from python_di_application.instance_cache import InstanceCache
from python_di_application.services.post_init_service import PostInitService

from python_di_application.services.registry_service import RegistryService
from python_di_application.services.resolution_service import ResolutionService

ParametersPostInit = ParamSpec("ParametersPostInit")
ReturnValuePostInit = TypeVar("ReturnValuePostInit")
post_init_signature = Callable[ParametersPostInit, ReturnValuePostInit]


class DIContainer:
    def __init__(self) -> None:
        self._registry_service = RegistryService()
        self._instance_cache = InstanceCache()
        self._resolution_service = ResolutionService(
            registry_service=self._registry_service,
            instance_cache=self._instance_cache,
        )
        self._post_init_service = PostInitService(
            resolution_service=self._resolution_service,
            instance_cache=self._instance_cache,
        )

    def register_instance[T](
        self, instance_obj: T, interface_type: type | None = None
    ) -> None:
        instance_type = interface_type if interface_type else type(instance_obj)
        self._instance_cache.store_singleton(
            dependency_type=instance_type,
            instance_obj=instance_obj,
        )
        self._registry_service.register_instance(
            instance_obj=instance_obj,
            interface_type=interface_type,
        )

    def reinitialize_dependency[T](self, interface_type: type[T]) -> T:
        self._instance_cache.delete_singleton(dependency_type=interface_type)
        return self[interface_type]

    def register_instances(self, instances: list[DependencyInstance]) -> None:
        for instance in instances:
            self.register_instance(
                instance_obj=instance.instance_obj,
                interface_type=instance.dependency_interface,
            )

    def register_dependency(self, dependency: Dependency) -> None:
        self._registry_service.upsert_dependency(dependency=dependency)

    def register_dependencies(
        self, dependencies_types_with_kwargs: list[Dependency[Any]]
    ) -> None:
        self._registry_service.register_dependencies(
            dependencies_types_with_kwargs=dependencies_types_with_kwargs
        )

    def override_dependencies(
        self, dependencies_types_with_kwargs: list[Dependency[Any]]
    ) -> None:
        self._registry_service.override_dependencies(
            dependencies_types_with_kwargs=dependencies_types_with_kwargs
        )

    def override_dependency(self, dependency: Dependency) -> None:
        self._registry_service.override_dependency(dependency=dependency)

    def replace_dependency_instance(
        self, dependency_instance: DependencyInstance
    ) -> None:
        replacement_dependency = self._registry_service.replace_dependency_instance(
            dependency_instance=dependency_instance
        )
        self._instance_cache.store_singleton(
            dependency_type=replacement_dependency.dependency_interface,
            instance_obj=dependency_instance.instance_obj,
        )

    def replace_dependency_instances(
        self, dependency_instances: list[DependencyInstance]
    ) -> None:
        for dependency_instance in dependency_instances:
            self.replace_dependency_instance(dependency_instance=dependency_instance)

    def resolve_dependency[T](self, dependency_type: type[T]) -> T:
        return self._resolution_service.resolve_dependency(
            dependency_type=dependency_type
        )

    def check_if_all_dependencies_are_used(self) -> None:
        for dependency in self._registry_service.get_registered_dependencies():
            if dependency.ignore_unused:
                continue
            if not self._instance_cache.was_dependency_used(
                dependency_type=dependency.dependency_interface
            ):
                raise ValueError(
                    f"Dependency {dependency.dependency_interface} not used"
                )

    def apply_post_init_wrappers(self) -> None:
        self._post_init_service.apply_post_init_wrappers()

    def __getitem__[T](self, item: type[T]) -> T:
        return self.resolve_dependency(dependency_type=item)

    @staticmethod
    def post_init_wrap(wrap_func: post_init_signature) -> post_init_signature:
        @functools.wraps(wrapped=wrap_func)
        def decorator(func: post_init_signature) -> post_init_signature:
            func.__post_init_wrapped__ = True  # type: ignore[attr-defined]
            func.__post_init_wrap_func__ = wrap_func  # type: ignore[attr-defined]
            return func

        return decorator
