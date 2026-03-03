import copy
import functools
import inspect
import logging
import os
import sys
from abc import ABC
from collections.abc import Callable
from dataclasses import dataclass
from inspect import Parameter
from typing import Any, ParamSpec, TypeVar
from unittest.mock import MagicMock

from pydantic.fields import FieldInfo
from pydantic_settings import BaseSettings

ParametersPostInit = ParamSpec("ParametersPostInit")
ReturnValuePostInit = TypeVar("ReturnValuePostInit")
post_init_signature = Callable[ParametersPostInit, ReturnValuePostInit]
# TestComment

logger = logging.getLogger(__name__)


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


class DIContainer:
    def __init__(self) -> None:
        self._registry: dict[type, Dependency] = {}
        self._singletons: dict[type, Any] = {}
        self._used_dependencies: list[type] = []

    def register_instance[T](
            self, instance_obj: T, interface_type: type | None = None
    ) -> None:
        instance_type = interface_type if interface_type else type(instance_obj)
        self._singletons[instance_type] = instance_obj
        if instance_type not in self._registry:
            self._registry[instance_type] = Dependency(
                dependency_type=type(instance_obj), dependency_interface=instance_type
            )

    def reinitialize_dependency[T](self, interface_type: type[T]) -> T:
        self._singletons.pop(interface_type, None)
        self.register_dependency(Dependency(interface_type))
        return self[interface_type]

    def register_instances(self, instances: list[DependencyInstance]) -> None:
        for instance in instances:
            self.register_instance(
                instance_obj=instance.instance_obj,
                interface_type=instance.dependency_interface,
            )

    def register_dependency(self, dependency: Dependency) -> None:
        """
        Registers a new dependency in the container.

        Args:
            dependency (Dependency): The Dependency object containing the type and
                                     arguments needed for instantiation.

        Returns:
            None
        """
        self._registry[dependency.dependency_interface] = dependency

    def register_dependencies(
            self, dependencies_types_with_kwargs: list[Dependency[Any]]
    ) -> None:
        for dependency in dependencies_types_with_kwargs:
            self.register_dependency(dependency=dependency)

    def override_dependencies(
            self, dependencies_types_with_kwargs: list[Dependency[Any]]
    ) -> None:
        for dependency in dependencies_types_with_kwargs:
            self.override_dependency(dependency=dependency)

    def override_dependency(self, dependency: Dependency) -> None:
        reg_dependency = self._registry.get(dependency.dependency_interface)
        if not reg_dependency:
            reg_dependency = self._find_dependency_in_registry(
                dependency_type=dependency.dependency_type
            )

        logger.debug(
            msg=f"Found dependency {reg_dependency} which will be overridden with {dependency}"
        )
        if reg_dependency:
            self._registry[reg_dependency.dependency_interface] = dependency
            return

        raise ValueError(
            f"Dependency {dependency.dependency_interface} konnte nicht im Registry gefunden oder überschrieben werden."
        )

    @staticmethod
    def _find_matching_subtypes(
            registered_type: type, dependency_interface: type, module: str
    ) -> bool:
        module_reg_type = registered_type.__module__.split(".")[0]
        subtypes = [
            sub_type
            for sub_type in inspect.getmro(registered_type)
            if module in sub_type.__module__ or module_reg_type in sub_type.__module__
        ]
        return any(
            sub_type in inspect.getmro(dependency_interface) for sub_type in subtypes
        )

    def replace_dependency_instance(
            self, dependency_instance: DependencyInstance
    ) -> None:
        reg_dependency = self._registry.get(dependency_instance.dependency_interface)
        if not reg_dependency:
            reg_dependency = self._find_dependency_in_registry(
                dependency_type=dependency_instance.dependency_interface
            )
        logger.debug(
            msg=f"Found dependency {reg_dependency} which will be replaced with instance"
                f" of type: {type(dependency_instance.instance_obj).__name__}"
        )
        if not reg_dependency:
            raise TypeError(f"Dependency {reg_dependency} not in")

        self._singletons[reg_dependency.dependency_interface] = (
            dependency_instance.instance_obj
        )

    def replace_dependency_instances(
            self, dependency_instances: list[DependencyInstance]
    ) -> None:
        for dep_instance in dependency_instances:
            self.replace_dependency_instance(dependency_instance=dep_instance)

    def resolve_dependency[T](self, dependency_type: type[T]) -> T:
        """
        Resolves and returns an instance of the given dependency type.

        If the dependency is found in the singleton cache, it is returned directly.
        Otherwise, the dependency is retrieved from the registry, instantiated,
        and added to the singleton cache.

        Args:
            dependency_type (Type[T]): The type of the dependency to resolve.

        Returns:
            T: The resolved dependency instance.
        """
        dependency = self._find_dependency_in_registry(dependency_type=dependency_type)
        instance_obj = self._resolve_singletons(
            dependency_type=dependency.dependency_interface
        )

        if not instance_obj:
            instance_obj = self._instantiate_dependency(dependency=dependency)
            self._singletons[dependency.dependency_interface] = instance_obj

        self._used_dependencies.append(dependency.dependency_interface)
        return instance_obj

    def check_if_all_dependencies_are_used(self) -> None:
        for dependency_interface, dep in self._registry.items():
            if dep.ignore_unused:
                continue

            if dep.dependency_interface not in self._used_dependencies:
                raise ValueError(f"Dependency {dependency_interface} not used")

    def _find_dependency_in_registry[T](self, dependency_type: type[T]) -> Dependency:
        dependency = self._registry.get(dependency_type, None)

        if dependency and dependency.is_abstract:
            raise TypeError(
                f"Registry returned abstract dependency {dependency.dependency_type}, "
                f"abstract dependencies need be to overwritten!"
            )

        if not dependency:
            dependency = self._try_to_find_subclass_in_registry(
                dependency_type=dependency_type
            )
        if not dependency:
            dependency = self._try_to_find_dependency_by_type_in_registry(
                dependency_type=dependency_type
            )
        logger.debug(
            msg=f"Found dependency {dependency} in registry for type {dependency_type.__name__}"
        )
        if not dependency:
            raise ValueError(f"Dependency {dependency_type} not found in registry")

        return dependency

    def _resolve_singletons[T](self, dependency_type: type[T]) -> T | None:
        singleton = None
        if dependency_type in self._singletons:
            singleton = self._singletons[dependency_type]
        return singleton

    def _try_to_find_subclass_in_registry[T](
            self, dependency_type: type[T]
    ) -> Dependency | None:
        subclasses = [
            cls for cls in self._registry if dependency_type in inspect.getmro(cls)
        ]
        if len(subclasses) > 1:
            raise ValueError(
                f"Ambiguous result multiple registered subclasses of {dependency_type} found"
            )
        elif len(subclasses) == 1:
            logger.debug(
                msg=f"Found subclass {subclasses[0]} in registry for type {dependency_type}"
            )
            return self._registry[subclasses[0]]
        else:
            return None

    def _try_to_find_dependency_by_type_in_registry[T](
            self, dependency_type: type[T]
    ) -> Dependency | None:
        dep_found = None
        for dependency in self._registry.values():
            if dependency.dependency_type in dependency_type.mro():
                dep_found = dependency
                break

        return dep_found

    def _instantiate_dependency[T](self, dependency: Dependency) -> T:  # type: ignore[type-var]
        """
        Instantiates a dependency using the provided type and arguments.

        Args:
            dependency_type (Type[T]): The type of the dependency to instantiate.
            kwargs (dict): Additional arguments for the dependency's constructor.

        Returns:
            T: The instantiated dependency object.
        """
        resolved_constructor_argument = {}
        signature_params = self._get_signature_arguments(
            dependency_type=dependency.dependency_type
        )

        if not dependency.is_abstract and tuple(signature_params.keys()) == (
                "args",
                "kwargs",
        ):
            return dependency.dependency_type()

        if BaseSettings in dependency.dependency_type.mro():
            env_prefix = dependency.dependency_type.model_config["env_prefix"]
            signature_params = {
                name if not field.alias else field.alias: Parameter(
                    name=name if not field.alias else field.alias,
                    kind=inspect._ParameterKind.KEYWORD_ONLY,
                    annotation=field.annotation,
                    default=self._build_pydantic_default(
                        field=field, name=name, env_prefix=env_prefix
                    ),
                )
                for name, field in dependency.dependency_type.model_fields.items()
            }

        for name, param in signature_params.items():
            if param.annotation is param.empty:
                raise ValueError(
                    f"Missing type annotation for {name} in {dependency.dependency_type.__name__}"
                )

            resolved_constructor_argument[name] = (
                self._resolve_dependency_from_annotation(
                    param_name=name, param=param, kwargs=dependency.kwargs
                )
            )
        return dependency.dependency_type(**resolved_constructor_argument)

    @staticmethod
    def _build_pydantic_default(field: FieldInfo, name: str, env_prefix: str) -> Any:
        env_var_name = (
            f"{env_prefix}{name}".upper() if not field.alias else field.alias.upper()
        )
        if var_value := os.getenv(env_var_name):
            return var_value
        return field.default

    def apply_post_init_wrappers(self) -> None:
        def get_class_instance[**P, T](func: Callable[P, T]) -> T:
            class_type = vars(sys.modules[func.__module__])[
                func.__qualname__.split(".")[0]
            ]
            if class_type not in self._singletons:
                dep = self.resolve_dependency(dependency_type=class_type)
            else:
                dep = self._singletons[class_type]
            return dep

        def get_post_init_func(singleton: object) -> list[tuple[Callable, Callable]]:
            funcs = [
                getattr(singleton, el)
                for el in dir(singleton)
                if hasattr(getattr(singleton, el), "__post_init_wrapped__")
            ]
            return [(func, func.__post_init_wrap_func__) for func in funcs]

        singletons = copy.deepcopy(list(self._singletons.keys()))

        for singleton in singletons:
            post_init_funcs = get_post_init_func(singleton=singleton)
            for func_to_wrap, post_init_func in post_init_funcs:
                wrapping_instance = get_class_instance(func=post_init_func)
                wrapped_instance = get_class_instance(func=func_to_wrap)
                func_to_wrap = getattr(wrapped_instance, func_to_wrap.__name__)
                wrapped_func = getattr(wrapping_instance, post_init_func.__name__)(
                    func_to_wrap
                )
                setattr(wrapped_instance, func_to_wrap.__name__, wrapped_func)

    def _resolve_dependency_from_annotation(
            self, param_name: str, param: Parameter, kwargs: dict[str, Any]
    ) -> Any:
        annotation = param.annotation

        # Use provided argument if available
        if param_name in kwargs:
            resolved_kwarg = kwargs[param_name]
        # Handle primitive types with default values
        elif param.default is not param.empty:
            resolved_kwarg = param.default
        else:
            # Resolve dependencies from the container
            resolved = self.resolve_dependency(dependency_type=annotation)
            resolved_kwarg = resolved

        return resolved_kwarg

    @staticmethod
    def _get_signature_arguments(dependency_type: type) -> dict[str, Parameter]:
        signature = inspect.signature(dependency_type.__init__)  # type: ignore[misc]
        parameters = {
            param_name: param
            for param_name, param in signature.parameters.items()
            if param_name != "self"
        }
        return parameters

    def __getitem__[T](self, item: type[T]) -> T:
        return self.resolve_dependency(dependency_type=item)

    def create_test_instance[T](
            self,
            dependency_type: type[T],
            override_instances: list[DependencyInstance] | None = None,
            override_dependencies: list[Dependency] | None = None,
    ) -> T:
        signature_params = self._get_signature_arguments(
            dependency_type=dependency_type
        )
        if override_instances:
            self.register_instances(instances=override_instances)
        if override_dependencies:
            self.register_dependencies(
                dependencies_types_with_kwargs=override_dependencies
            )

        constructor_arguments: dict[str, MagicMock] = {}
        for name, param in signature_params.items():
            try:
                constructor_arguments[name] = self.resolve_dependency(
                    dependency_type=param.annotation
                )
            except ValueError:
                mock = MagicMock(spec=param.annotation)
                constructor_arguments[name] = mock
                self.register_instance(
                    instance_obj=mock,
                    interface_type=param.annotation,
                )
        dep_instance = dependency_type(**constructor_arguments)
        self.register_instance(instance_obj=dep_instance)
        self.apply_post_init_wrappers()
        return self[dependency_type]

    @staticmethod
    def post_init_wrap(wrap_func: post_init_signature) -> post_init_signature:
        @functools.wraps(wrapped=wrap_func)
        def decorator(func: post_init_signature) -> post_init_signature:
            func.__post_init_wrapped__ = True  # type: ignore[attr-defined]
            func.__post_init_wrap_func__ = wrap_func  # type: ignore[attr-defined]
            return func

        return decorator
