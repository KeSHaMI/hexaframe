from typing import Any, Callable, Generic, Type, TypeVar

from fastapi import APIRouter, Depends, FastAPI, Response

from hexaframe.use_case import AbstractUseCase

InputDTO = TypeVar("InputDTO")
OutputDTO = TypeVar("OutputDTO")


class Endpoint(Generic[InputDTO, OutputDTO]):
    def __init__(
        self,
        path: str,
        interactor: Callable[..., AbstractUseCase[InputDTO, OutputDTO]],
        input_adapter: Callable[..., InputDTO],
        output_adapter: Callable[[OutputDTO], Response],
        methods: list[str] | None = None,
        **kwargs: Any,
    ):
        self.path = path
        self.interactor = interactor
        self.input_adapter = input_adapter
        self.output_adapter = output_adapter
        self.methods = methods or ["GET"]
        self.kwargs = kwargs

    def register(self, router: APIRouter) -> None:
        handler = self._create_handler()
        router.add_api_route(self.path, handler, methods=self.methods, **self.kwargs)

    def _get_use_case(self) -> AbstractUseCase[InputDTO, OutputDTO]:
        return self.interactor()

    def _create_handler(self) -> Callable[..., Any]:
        from inspect import Parameter, signature

        adapter_sig = signature(self.input_adapter)
        adapter_params = list(adapter_sig.parameters.values())

        use_case_param = Parameter(
            "use_case",
            Parameter.KEYWORD_ONLY,
            default=Depends(self._get_use_case),
            annotation=AbstractUseCase[InputDTO, OutputDTO],
        )

        handler_params = adapter_params + [use_case_param]

        final_signature = signature(self.input_adapter).replace(
            parameters=handler_params,
            return_annotation=Response,
        )

        async def handler(**kwargs: Any) -> Response:
            use_case = kwargs.pop("use_case")
            adapter_kwargs = {
                k: v for k, v in kwargs.items() if k in adapter_sig.parameters
            }
            input_dto = self.input_adapter(**adapter_kwargs)
            output_dto = use_case.execute(input_dto)
            return self.output_adapter(output_dto)

        handler.__signature__ = final_signature

        return handler


def register_endpoints(app: FastAPI, resources: list[Type[Any]]) -> None:
    router = APIRouter()
    for resource in resources:
        for endpoint in vars(resource).values():
            if isinstance(endpoint, Endpoint):
                endpoint.register(router)
    app.include_router(router)
