from typing import Any


class InstanceCache:
    def __init__(self) -> None:
        self._singletons: dict[type, Any] = {}
        self._used_dependencies: set[type] = set()

    def __getitem__[T](self, item: type[T]) -> T | None:
        return self._singletons.get(item)

    def store_singleton[T](self, dependency_type: type[T], instance_obj: T) -> None:
        self._singletons[dependency_type] = instance_obj

    def delete_singleton(self, dependency_type: type) -> None:
        self._singletons.pop(dependency_type, None)

    def mark_dependency_as_used(self, dependency_type: type) -> None:
        self._used_dependencies.add(dependency_type)

    def was_dependency_used(self, dependency_type: type) -> bool:
        return dependency_type in self._used_dependencies

    def get_singleton_types(self) -> list[type]:
        return list(self._singletons.keys())
