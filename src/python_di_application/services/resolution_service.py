import inspect
import logging
import os
from inspect import Parameter
from typing import Any, cast

from pydantic.fields import FieldInfo
from pydantic_settings import BaseSettings

from python_di_application.dependency import Dependency
from python_di_application.instance_cache import InstanceCache
from python_di_application.services.registry_service import RegistryService

logger = logging.getLogger(__name__)


class ResolutionService:
    def __init__(
        self,
        registry_service: RegistryService,
        instance_cache: InstanceCache,
    ) -> None:
        self._registry_service = registry_service
        self._instance_cache = instance_cache

    def resolve_dependency[T](self, dependency_type: type[T]) -> T:
        dependency = self.find_dependency_in_registry(dependency_type=dependency_type)
        instance_obj = self._instance_cache[dependency.dependency_interface]

        if instance_obj is None:
            instance_obj = self._instantiate_dependency(dependency=dependency)
            self._instance_cache.store_singleton(
                dependency_type=dependency.dependency_interface,
                instance_obj=instance_obj,
            )

        self._instance_cache.mark_dependency_as_used(
            dependency_type=dependency.dependency_interface
        )
        return instance_obj

    def find_dependency_in_registry[T](self, dependency_type: type[T]) -> Dependency:
        dependency = self._registry_service.get_direct_dependency(
            dependency_type=dependency_type
        )

        if dependency and dependency.is_abstract:
            raise TypeError(
                f"Registry returned abstract dependency {dependency.dependency_type}, "
                f"abstract dependencies need be to overwritten!"
            )

        if not dependency:
            dependency = self._registry_service.find_registered_dependency(
                dependency_type=dependency_type
            )

        logger.debug(
            msg=f"Found dependency {dependency} in registry for type {dependency_type.__name__}"
        )
        if not dependency:
            raise ValueError(f"Dependency {dependency_type} not found in registry")

        return dependency

    def _instantiate_dependency[T](self, dependency: Dependency[T]) -> T:
        resolved_constructor_argument = {}
        signature_params = self.get_signature_arguments(
            dependency_type=dependency.dependency_type
        )

        if not dependency.is_abstract and tuple(signature_params.keys()) == (
            "args",
            "kwargs",
        ):
            # If the dependency only has a constructor with *args and **kwargs,
            # we assume that it can be instantiated without any arguments.
            return dependency.dependency_type()

        if BaseSettings in dependency.dependency_type.mro():
            settings_type = cast(type[BaseSettings], dependency.dependency_type)
            env_prefix = settings_type.model_config["env_prefix"]
            signature_params = {
                name if not field.alias else field.alias: Parameter(
                    name=name if not field.alias else field.alias,
                    kind=inspect._ParameterKind.KEYWORD_ONLY,
                    annotation=field.annotation,
                    default=self._build_pydantic_default(
                        field=field, name=name, env_prefix=env_prefix
                    ),
                )
                for name, field in settings_type.model_fields.items()
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

    def _resolve_dependency_from_annotation(
        self, param_name: str, param: Parameter, kwargs: dict[str, Any]
    ) -> Any:
        annotation = param.annotation

        if param_name in kwargs:
            return kwargs[param_name]
        if param.default is not param.empty:
            return param.default
        return self.resolve_dependency(dependency_type=annotation)

    @staticmethod
    def get_signature_arguments(dependency_type: type) -> dict[str, Parameter]:
        signature = inspect.signature(dependency_type)
        return {
            param_name: param
            for param_name, param in signature.parameters.items()
            if param_name != "self"
        }
