from python_di.application import Application
from python_di.di_container import DIContainer, Dependency
from python_di.example.services.config_b import ConfigB

from python_di.example.services.service_a import ServiceA
from python_di.example.services.service_b import ServiceB


class ExampleApp(Application):

    def __init__(self, service_a: ServiceA) -> None:
        self._service_a = service_a

    @classmethod
    def _default_container(cls) -> DIContainer:
        di = DIContainer()
        di.register_dependencies(
            dependencies_types_with_kwargs=[
                Dependency(ServiceA),
                Dependency(ServiceB),
                Dependency(ConfigB),
                Dependency(cls)
            ]
        )
        return di


    @classmethod
    def _build(cls, container: DIContainer) -> tuple[DIContainer, 'ExampleApp']:
        return container, container.resolve_dependency(dependency_type=cls)


    def run(self):
        self._service_a.do_random()
