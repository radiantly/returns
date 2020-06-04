from typing import Any, Awaitable, Callable, ClassVar, Generic, TypeVar, Union

from typing_extensions import final

from returns._generated.futures import _future_result
from returns.context import NoDeps
from returns.future import FutureResult
from returns.io import IO
from returns.primitives.container import BaseContainer

# Context:
_EnvType = TypeVar('_EnvType', contravariant=True)

# Result:
_ValueType = TypeVar('_ValueType', covariant=True)
_NewValueType = TypeVar('_NewValueType')
_ErrorType = TypeVar('_ErrorType', covariant=True)
_NewErrorType = TypeVar('_NewErrorType')

# Helpers:
_FirstType = TypeVar('_FirstType')


@final
class RequiresContextFutureResult(
    BaseContainer,
    Generic[_EnvType, _ValueType, _ErrorType],
):
    """Someday this container will grow very big."""

    #: Inner value of `RequiresContext`
    #: is just a function that returns `FutureResult`.
    #: This field has an extra 'RequiresContext' just because `mypy` needs it.
    _inner_value: Callable[
        ['RequiresContextFutureResult', _EnvType],
        FutureResult[_ValueType, _ErrorType],
    ]

    #: A convinient placeholder to call methods created by `.from_value()`.
    empty: ClassVar[NoDeps] = object()

    def __init__(
        self,
        inner_value: Callable[[_EnvType], FutureResult[_ValueType, _ErrorType]],
    ) -> None:
        """
        Public constructor for this type. Also required for typing.

        Only allows functions of kind ``* -> *``
        and returning :class:`returns.result.Result` instances.

        .. code:: python

          >>> from returns.context import RequiresContextFutureResult
          >>> from returns.future import FutureResult

          >>> instance = RequiresContextFutureResult(
          ...    lambda deps: FutureResult.from_value(1),
          ... )
          >>> str(instance)
          '<RequiresContextFutureResult: <function <lambda> at ...>>'

        """
        super().__init__(inner_value)

    def __call__(self, deps: _EnvType) -> FutureResult[_ValueType, _ErrorType]:
        """
        Evaluates the wrapped function.

        .. code:: python

          >>> import anyio
          >>> from returns.context import RequiresContextFutureResult
          >>> from returns.future import FutureResult
          >>> from returns.io import IOSuccess

          >>> def first(lg: bool) -> RequiresContextFutureResult[int, int, str]:
          ...     # `deps` has `int` type here:
          ...     return RequiresContextFutureResult(
          ...         lambda deps: FutureResult.from_value(
          ...             deps if lg else -deps,
          ...         ),
          ...     )

          >>> instance = first(False)
          >>> assert anyio.run(instance(3).awaitable) == IOSuccess(-3)

          >>> instance = first(True)
          >>> assert anyio.run(instance(3).awaitable) == IOSuccess(3)

        In other things, it is a regular Python magic method.

        """
        return self._inner_value(deps)

    def map(  # noqa: WPS125
        self,
        function: Callable[[_ValueType], _NewValueType],
    ) -> 'RequiresContextFutureResult[_EnvType, _NewValueType, _ErrorType]':
        """
        Composes successful container with a pure function.

        .. code:: python

          >>> import anyio
          >>> from returns.context import RequiresContextFutureResult
          >>> from returns.io import IOSuccess, IOFailure

          >>> assert anyio.run(RequiresContextFutureResult.from_value(1).map(
          ...     lambda x: x + 1,
          ... )(...).awaitable) == IOSuccess(2)

          >>> assert anyio.run(RequiresContextFutureResult.from_failure(1).map(
          ...     lambda x: x + 1,
          ... )(...).awaitable) == IOFailure(1)

        """
        return RequiresContextFutureResult(
            lambda deps: self(deps).map(function),
        )

    def bind(
        self,
        function: Callable[
            [_ValueType],
            'RequiresContextFutureResult[_EnvType, _NewValueType, _ErrorType]',
        ],
    ) -> 'RequiresContextFutureResult[_EnvType, _NewValueType, _ErrorType]':
        """
        Composes this container with a function returning the same type.

        .. code:: python

          >>> import anyio
          >>> from returns.context import RequiresContextFutureResult
          >>> from returns.future import FutureResult
          >>> from returns.io import IOSuccess, IOFailure

          >>> def first(lg: bool) -> RequiresContextFutureResult[int, int, int]:
          ...     # `deps` has `int` type here:
          ...     return RequiresContextFutureResult(
          ...         lambda deps: FutureResult.from_value(
          ...             deps,
          ...         ) if lg else FutureResult.from_failure(-deps),
          ...     )

          >>> def second(
          ...     number: int,
          ... ) -> RequiresContextFutureResult[int, str, int]:
          ...     # `deps` has `int` type here:
          ...     return RequiresContextFutureResult(
          ...         lambda deps: FutureResult.from_value(str(number + deps)),
          ...     )

          >>> assert anyio.run(
          ...     first(True).bind(second)(1).awaitable,
          ... ) == IOSuccess('2')
          >>> assert anyio.run(
          ...     first(False).bind(second)(2).awaitable,
          ... ) == IOFailure(-2)

        """
        return RequiresContextFutureResult(
            lambda deps: self(deps).bind(
                lambda inner: function(inner)(deps),  # type: ignore
            ),
        )

    def rescue(
        self,
        function: Callable[
            [_ErrorType],
            'RequiresContextFutureResult[_EnvType, _ValueType, _NewErrorType]',
        ],
    ) -> 'RequiresContextFutureResult[_EnvType, _ValueType, _NewErrorType]':
        """
        Composes this container with a function returning the same type.

        .. code:: python

          >>> import anyio
          >>> from returns.context import RequiresContextFutureResult
          >>> from returns.future import FutureResult
          >>> from returns.io import IOSuccess, IOFailure

          >>> def rescuable(
          ...     arg: str,
          ... ) -> RequiresContextFutureResult[str, str, str]:
          ...      return RequiresContextFutureResult(
          ...          lambda deps: FutureResult.from_value(
          ...              deps + arg,
          ...          ) if len(arg) > 1 else FutureResult.from_failure(
          ...              arg + deps,
          ...          ),
          ...      )

          >>> assert anyio.run(
          ...     RequiresContextFutureResult.from_value('a').rescue(rescuable),
          ...     'c',
          ... ) == IOSuccess('a')

          >>> assert anyio.run(
          ...     RequiresContextFutureResult.from_failure('a').rescue(
          ...         rescuable,
          ...     ),
          ...     'c',
          ... ) == IOFailure('ac')

          >>> assert anyio.run(
          ...     RequiresContextFutureResult.from_failure('aa').rescue(
          ...         rescuable,
          ...     ),
          ...     'b',
          ... ) == IOSuccess('baa')

        """
        return RequiresContextFutureResult(
            lambda deps: self(deps).rescue(
                lambda inner: function(inner)(deps),  # type: ignore
            ),
        )

    def value_or(  # noqa: WPS234
        self, default_value: _FirstType,
    ) -> Callable[
        [_EnvType],
        Awaitable[IO[Union[_ValueType, _FirstType]]],
    ]:
        """
        Returns a callable that either returns a success or default value.

        .. code:: python

          >>> import anyio
          >>> from returns.context import RequiresContextFutureResult
          >>> from returns.io import IO

          >>> assert anyio.run(
          ...     RequiresContextFutureResult.from_value(1).value_or(2),
          ...     RequiresContextFutureResult.empty,
          ... ) == IO(1)

          >>> assert anyio.run(
          ...     RequiresContextFutureResult.from_failure(1).value_or(2),
          ...     RequiresContextFutureResult.empty,
          ... ) == IO(2)

        """
        return lambda deps: _future_result.async_value_or(
            self(deps), default_value,
        )

    def unwrap(self) -> Callable[[_EnvType], Awaitable[IO[_ValueType]]]:
        """
        Returns a callable that unwraps success value or raises exception.

        .. code:: pycon

          >>> import anyio
          >>> from returns.context import RequiresContextFutureResult
          >>> from returns.io import IO

          >>> assert anyio.run(
          ...     RequiresContextFutureResult.from_value(1).unwrap(),
          ...     RequiresContextFutureResult.empty,
          ... ) == IO(1)

          >>> anyio.run(
          ...     RequiresContextFutureResult.from_failure(1).unwrap(),
          ...     RequiresContextFutureResult.empty,
          ... )
          Traceback (most recent call last):
            ...
          returns.primitives.exceptions.UnwrapFailedError

        """
        return lambda deps: _future_result.async_unwrap(self(deps))

    def failure(self) -> Callable[[_EnvType], Awaitable[IO[_ErrorType]]]:
        """
        Returns a callable that unwraps failure value or raises exception.

        .. code:: pycon

          >>> import anyio
          >>> from returns.context import RequiresContextFutureResult
          >>> from returns.io import IO

          >>> assert anyio.run(
          ...     RequiresContextFutureResult.from_failure(1).failure(),
          ...     RequiresContextFutureResult.empty,
          ... ) == IO(1)

          >>> anyio.run(
          ...    RequiresContextFutureResult.from_value(1).failure(),
          ...    RequiresContextFutureResult.empty,
          ... )
          Traceback (most recent call last):
            ...
          returns.primitives.exceptions.UnwrapFailedError

        """
        return lambda deps: _future_result.async_failure(self(deps))

    @classmethod
    def from_value(
        cls, inner_value: _FirstType,
    ) -> 'RequiresContextFutureResult[NoDeps, _FirstType, Any]':
        """
        Creates new container with successful ``FutureResult`` as a unit value.

        .. code:: python

          >>> import anyio
          >>> from returns.context import RequiresContextFutureResult
          >>> from returns.io import IOSuccess

          >>> assert anyio.run(RequiresContextFutureResult.from_value(1)(
          ...    RequiresContextFutureResult.empty,
          ... ).awaitable) == IOSuccess(1)

        """
        return RequiresContextFutureResult(
            lambda _: FutureResult.from_value(inner_value),
        )

    @classmethod
    def from_failure(
        cls, inner_value: _FirstType,
    ) -> 'RequiresContextFutureResult[NoDeps, Any, _FirstType]':
        """
        Creates new container with failed ``FutureResult`` as a unit value.

        .. code:: python

          >>> import anyio
          >>> from returns.context import RequiresContextFutureResult
          >>> from returns.io import IOFailure

          >>> assert anyio.run(RequiresContextFutureResult.from_failure(1)(
          ...     RequiresContextFutureResult.empty,
          ... ).awaitable) == IOFailure(1)

        """
        return RequiresContextFutureResult(
            lambda _: FutureResult.from_failure(inner_value),
        )


# Aliases:

#: Alias for a popular case when ``Result`` has ``Exception`` as error type.
RequiresContextFutureResultE = RequiresContextFutureResult[
    _EnvType, _ValueType, Exception,
]

#: Sometimes `RequiresContextFutureResult` is too long to type.
ReaderFutureResult = RequiresContextFutureResult

#: Alias to save you some typing. Uses ``Exception`` as error type.
ReaderFutureResultE = RequiresContextFutureResult[
    _EnvType, _ValueType, Exception,
]
