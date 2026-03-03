from python_di_application.example.services.config_b import ConfigB


class ServiceB:

    def __init__(self, config_b: ConfigB) -> None:
        self._config_b = config_b

    def __call__(self) -> None:
        print(f"ServiceB {self._config_b.config_b}")