from unittest.mock import MagicMock

from python_di_application.dependency import Dependency, DependencyInstance
from python_di_application.di_container import DIContainer


class TestDIContainer(DIContainer):
    def create_test_instance[T](
        self,
        dependency_type: type[T],
        override_instances: list[DependencyInstance] | None = None,
        override_dependencies: list[Dependency] | None = None,
    ) -> T:
        signature_params = self._resolution_service.get_signature_arguments(
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
