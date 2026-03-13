import copy
import sys
from typing import Any, Protocol

from python_di_application.instance_cache import InstanceCache
from python_di_application.services.resolution_service import ResolutionService


class PostInitCallable(Protocol):
    __module__: str
    __qualname__: str
    __name__: str
    __post_init_wrap_func__: "PostInitCallable"

    def __call__(self, *args: Any, **kwargs: Any) -> Any: ...


class PostInitService:
    def __init__(
        self,
        resolution_service: ResolutionService,
        instance_cache: InstanceCache,
    ) -> None:
        self._resolution_service = resolution_service
        self._instance_cache = instance_cache

    def apply_post_init_wrappers(self) -> None:
        def get_class_instance(func: PostInitCallable) -> object:
            class_type = vars(sys.modules[func.__module__])[
                func.__qualname__.split(".")[0]
            ]
            singleton = self._instance_cache[class_type]
            if singleton is None:
                return self._resolution_service.resolve_dependency(
                    dependency_type=class_type
                )
            return singleton

        def get_post_init_func(
            singleton: object,
        ) -> list[tuple[PostInitCallable, PostInitCallable]]:
            funcs: list[PostInitCallable] = [
                getattr(singleton, el)
                for el in dir(singleton)
                if hasattr(getattr(singleton, el), "__post_init_wrapped__")
            ]
            return [(func, func.__post_init_wrap_func__) for func in funcs]

        singletons = copy.deepcopy(x=self._instance_cache.get_singleton_types())

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
