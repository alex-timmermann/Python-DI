from python_di_application.example.services.service_b import ServiceB


class ServiceA:

    def __init__(self, service_b: ServiceB) -> None:
        self._service_b = service_b

    def do_random(self) -> None:
        self._service_b()