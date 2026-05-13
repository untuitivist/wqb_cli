"""
功能概述
`wqb_core.datetime_range` 模块。

这个文件提供 `DatetimeRange` 时间范围工具，用于按固定时间步长表示半开区间时间序列。

主推荐入口
- `DatetimeRange(...)`

适用场景
- 按固定步长生成时间点序列
- 需要像 `range` 一样对 `datetime` 区间做切片、迭代和包含判断

注意事项
- 本文件中的中文说明已按 UTF-8 重写。
- `DatetimeRange` 采用半开区间语义，即包含 `start` 不包含 `stop`。
"""

from collections.abc import Iterator, Sequence
from datetime import datetime, timedelta
from typing import Self, SupportsIndex, final, overload

__all__ = ['DatetimeRange']


@final
class DatetimeRange(Sequence[datetime]):
    """
    表示按固定时间步长展开的 `datetime` 半开区间。

    该类型在语义上类似 Python 内置 `range`，但元素类型是 `datetime`，
    步长类型是 `timedelta`。
    """

    __slots__ = (
        '__start',
        '__stop',
        '__step',
    )

    __start: datetime
    __stop: datetime
    __step: timedelta

    def __init__(
        self,
        start: datetime,
        stop: datetime,
        step: timedelta,
        /,
    ) -> None:
        if not step:
            raise ValueError(f"DatetimeRange() arg 3 must not be <{step}>")
        self.__start = start
        self.__stop = stop
        self.__step = step

    @property
    def start(
        self,
        /,
    ) -> datetime:
        """
        返回起始时间。
        """
        return self.__start

    @property
    def stop(
        self,
        /,
    ) -> datetime:
        """
        返回结束时间。
        """
        return self.__stop

    @property
    def step(
        self,
        /,
    ) -> timedelta:
        """
        返回时间步长。
        """
        return self.__step

    def __repr__(
        self,
        /,
    ) -> str:
        return f"DatetimeRange(<{self.start}>, <{self.stop}>, <{self.step}>)"

    def __eq__(
        self,
        other: object,
        /,
    ) -> bool:
        if not isinstance(other, DatetimeRange):
            return False
        return (
            self.start == other.start
            and self.stop == other.stop
            and self.step == other.step
        )

    def __hash__(
        self,
        /,
    ) -> int:
        return hash((self.start, self.stop, self.step))

    def __len__(
        self,
        /,
    ) -> int:
        return (self.stop - self.start) // self.step

    def __iter__(
        self,
        /,
    ) -> Iterator[datetime]:
        stop = self.stop
        step = self.step
        current = self.start
        while current < stop:
            yield current
            current += step

    def __reversed__(
        self,
        /,
    ) -> Iterator[datetime]:
        start = self.start
        step = self.step
        current = start + step * (len(self) - 1)
        while start <= current:
            yield current
            current -= step

    @overload
    def __getitem__(
        self,
        key: SupportsIndex,
        /,
    ) -> datetime: ...

    @overload
    def __getitem__(
        self,
        key: slice,
        /,
    ) -> Self: ...

    def __getitem__(
        self,
        key: SupportsIndex | slice,
        /,
    ) -> datetime | Self:
        if isinstance(key, SupportsIndex):
            index = key.__index__()
            length = len(self)
            if index < 0:
                index += length
            if not 0 <= index < length:
                raise IndexError('DatetimeRange index out of range')
            res = self.start + self.step * index
        elif isinstance(key, slice):
            start = key.start
            stop = key.stop
            step = key.step
            length = len(self)
            if start is None:
                start = 0
            else:
                if not isinstance(start, SupportsIndex):
                    raise TypeError(
                        'slice indices must be integers or None or have an __index__ method'
                    )
                start = start.__index__()
                if start < 0:
                    start += length
                start = min(max(start, 0), length - 1)
            if stop is None:
                stop = length
            else:
                if not isinstance(stop, SupportsIndex):
                    raise TypeError(
                        'slice indices must be integers or None or have an __index__ method'
                    )
                stop = stop.__index__()
                if stop < 0:
                    stop += length
                stop = min(max(stop, 0), length - 1)
            if step is None:
                step = 1
            else:
                if not isinstance(step, SupportsIndex):
                    raise TypeError(
                        'slice indices must be integers or None or have an __index__ method'
                    )
                step = step.__index__()
                if 0 == step:
                    raise ValueError('slice step cannot be zero')
            return self.__class__(
                self.start + self.step * start,
                self.start + self.step * stop,
                self.step * step,
            )
        else:
            raise TypeError(
                f"DatetimeRange indices must be integers or slices, not {type(key).__name__}"
            )
        return res

    def __contains__(
        self,
        key: object,
        /,
    ) -> bool:
        if not isinstance(key, datetime):
            return False
        if self.start <= key < self.stop:
            td = (key - self.start) % self.step
            return 0 == td.days == td.seconds == td.microseconds
        return False

    def count(
        self,
        key: datetime,
        /,
    ) -> int:
        """
        统计某个时间点在区间中的出现次数。
        """
        return int(key in self)

    def index(
        self,
        key: datetime,
        /,
    ) -> int:
        """
        返回某个时间点在区间中的索引。
        """
        if key not in self:
            raise ValueError(f'{key!r} is not in range')
        return (key - self.start) // self.step
