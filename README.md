# Python-DI
Python-DI is a lightweight dependency injection container for Python applications.
It automatically resolves constructor dependencies, supports singleton-style
instance reuse, and allows runtime overrides for both dependencies and
configuration objects (for example `pydantic` settings), as demonstrated in the
`src/python_di/example` application.

## Entry point example

```python
from python_di.di_container import DependencyInstance
from python_di.example.example_app import ExampleApp
from python_di.example.services.config_b import ConfigB


def main():
    app = ExampleApp.build()
    app.run()

    # or override the dependencies
    app_2 = ExampleApp.build(
        override_instances=[
            DependencyInstance(instance_obj=ConfigB(config_b="override")),
        ]
    )
    app_2.run()


if __name__ == "__main__":
    main()
```

## Example app

```python
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
                Dependency(cls),
            ]
        )
        return di

    @classmethod
    def _build(cls, container: DIContainer) -> tuple[DIContainer, "ExampleApp"]:
        return container, container.resolve_dependency(dependency_type=cls)

    def run(self):
        self._service_a.do_random()
```

## How the setup works

Start with the `Entry point example`: `main()` calls `ExampleApp.build()` and then
`app.run()`.

In the `Example app`, `_default_container()` defines the dependency graph by
registering `ServiceA`, `ServiceB`, `ConfigB`, and `ExampleApp` itself. During
`build()`, the container resolves constructor dependencies from type hints:

- `ExampleApp` needs `ServiceA`
- `ServiceA` needs `ServiceB`
- `ServiceB` needs `ConfigB`

That means you only declare dependencies in constructors, and the container wires
the full object graph automatically.

## Why this is useful

The two examples together show the main advantages of `python-di`:

- Centralized wiring: dependency registration is in one place (`_default_container()`),
  instead of scattered factory code.
- Cleaner services: service classes only declare what they need in `__init__`,
  without manually instantiating collaborators.
- Easy runtime overrides: the `Entry point example` shows
  `override_instances=[DependencyInstance(...)]`, which lets you swap config or
  test doubles without changing application code.
- Better testability: because dependencies are injected, unit tests can replace
  concrete objects with lightweight alternatives.
