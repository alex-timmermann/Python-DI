import logging
from abc import ABC, abstractmethod
from typing import Any

from python_di_application.di_container import Dependency, DependencyInstance, DIContainer


class Application(ABC):
    @classmethod
    def default_container(
        cls,
        override_dependencies: list[Dependency[Any]] | None = None,
        override_instances: list[DependencyInstance] | None = None,
    ) -> DIContainer:
        container = cls._default_container()
        if override_dependencies:
            container.override_dependencies(
                dependencies_types_with_kwargs=override_dependencies
            )
        if override_instances:
            container.replace_dependency_instances(
                dependency_instances=override_instances
            )
        return container

    @classmethod
    @abstractmethod
    def _default_container(cls) -> DIContainer:
        pass

    @classmethod
    def build[T](
        cls: type[T],
        container: DIContainer | None = None,
        override_dependencies: list[Dependency] | None = None,
        override_instances: list[DependencyInstance] | None = None,
        ignore_unused_dependencies: bool = False,
    ) -> T:
        if container is None:
            container = cls.default_container(  # type: ignore[attr-defined]
                override_dependencies=override_dependencies,
                override_instances=override_instances,
            )

        container, application = cls._build(container=container)  # type: ignore[attr-defined]

        application._attach_container(container=container)

        if not isinstance(container, DIContainer):
            raise TypeError(
                f"Container must be an instance of DIContainer, but got {type(container)}"
            )
        container.apply_post_init_wrappers()
        if not ignore_unused_dependencies:
            container.check_if_all_dependencies_are_used()

        logger = logging.getLogger("py4j")
        logger.setLevel(logging.WARNING)
        return application

    @classmethod
    @abstractmethod
    def _build[T](cls: type[T], container: DIContainer) -> tuple[DIContainer, T]:
        pass

    def _attach_container(self, container: DIContainer) -> None:
        self._container = container

    def __getitem__[T](self, item: type[T]) -> T:
        return self._container[item]
