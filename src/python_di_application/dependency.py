from abc import ABC
from dataclasses import dataclass
from typing import Any


@dataclass
class Dependency[T]:
    """
    Represents a dependency with its type, interface, and additional options.

    This class is used to define a dependency along with its corresponding type,
    interface, and any optional keyword arguments that may be required. It also
    determines whether the provided dependency type is abstract, allowing for
    further customization and behavior control.

    :ivar dependency_type: The concrete type of the dependency.
    :type dependency_type: type[T]
    :ivar dependency_interface: The interface type representing the dependency.
    :type dependency_interface: type[T]
    :ivar ignore_unused: Indicates whether to ignore this dependency when it is
        unused. Defaults to True if the dependency type is abstract.
    :type ignore_unused: bool
    :ivar kwargs: Additional keyword arguments associated with the dependency.
    :type kwargs: dict[str, Any]
    """

    dependency_type: type[T]
    dependency_interface: type[T]
    kwargs: dict[str, Any]

    def __init__(
        self,
        dependency_type: type[T],
        dependency_interface: type | None = None,
        ignore_unused: bool = False,
        **kwargs: Any,
    ):
        self.dependency_type = dependency_type
        self.dependency_interface = (
            dependency_interface if dependency_interface else dependency_type
        )
        self._is_abstract = self._dependency_type_is_abstract()
        self.ignore_unused = ignore_unused or self._is_abstract
        self.kwargs = kwargs

    def _dependency_type_is_abstract(self) -> bool:
        return self.dependency_type.mro()[1] == ABC

    @property
    def is_abstract(self) -> bool:
        return self._is_abstract

    def __str__(self):
        return (
            f"Dep<Interface: {self.dependency_interface.__name__}, "
            f" Type: {self.dependency_type.__name__}>"
        )


@dataclass
class DependencyInstance[T]:
    instance_obj: T
    dependency_interface: type[T]

    def __init__(self, instance_obj: T, dependency_interface: type | None = None):
        self.instance_obj = instance_obj
        self.dependency_interface = (
            dependency_interface if dependency_interface else type(instance_obj)
        )
