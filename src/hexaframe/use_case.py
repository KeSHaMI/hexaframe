from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Generic, TypeVar

from .errors import HexaError
from .result import Err, Ok, Result

InputT = TypeVar("InputT")  # Input DTO
OutputT = TypeVar("OutputT")  # Output DTO


class UseCase(Generic[InputT, OutputT], ABC):
    """
    Synchronous use case base.

    Subclasses implement `perform(input)` and may override hooks:
      - validate(input): raise DomainError/ValidationError to fail fast
      - before(input): side-effect hook before execution
      - after(result): side-effect hook after execution

    Execution contract:
      - Returns Result[O, HexaError]
      - Exceptions of type HexaError are captured as Err
      - Other exceptions are propagated (let calling layer decide)
    """

    def execute(self, input: InputT) -> Result[OutputT, HexaError]:
        try:
            self.validate(input)
            self.before(input)
            out = self.perform(input)
            res: Result[OutputT, HexaError] = (
                out if isinstance(out, Result) else Ok(out)
            )  # type: ignore[assignment]
            self.after(res)
            return res
        except HexaError as he:
            res = Err(he)
            self.after(res)
            return res

    # Hooks ------------------------------------------------------------------

    def validate(self, input: InputT) -> None:
        return None

    def before(self, input: InputT) -> None:
        return None

    def after(self, result: Result[OutputT, HexaError]) -> None:
        return None

    # Implementation point ---------------------------------------------------

    @abstractmethod
    def perform(self, input: InputT) -> OutputT | Result[OutputT, HexaError]:
        """
        Implement the use case business logic.

        May return a plain output (wrapped into Ok) or a Result.
        Raise HexaError to signal domain/infra failures that should map to Err.
        """
        raise NotImplementedError


class AsyncUseCase(Generic[InputT, OutputT], ABC):
    """
    Asynchronous use case base.

    Subclasses implement `aperform(input)` and may override hooks:
      - avalidate(input)
      - abefore(input)
      - aafter(result)

    Execution contract mirrors UseCase, but async.
    """

    async def execute(self, input: InputT) -> Result[OutputT, HexaError]:
        try:
            await self.avalidate(input)
            await self.abefore(input)
            out = await self.aperform(input)
            res: Result[OutputT, HexaError] = (
                out if isinstance(out, Result) else Ok(out)
            )  # type: ignore[assignment]
            await self.aafter(res)
            return res
        except HexaError as he:
            res = Err(he)
            await self.aafter(res)
            return res

    # Hooks ------------------------------------------------------------------

    async def avalidate(self, input: InputT) -> None:
        return None

    async def abefore(self, input: InputT) -> None:
        return None

    async def aafter(self, result: Result[OutputT, HexaError]) -> None:
        return None

    # Implementation point ---------------------------------------------------

    @abstractmethod
    async def aperform(self, input: InputT) -> OutputT | Result[OutputT, HexaError]:
        """
        Implement the use case business logic (async).
        """
        raise NotImplementedError
