from sys import version_info
from pathlib import Path
from os import stat
from asyncio import Task, sleep, get_event_loop
from functools import partial
from enum import Enum
from typing import Any, Callable, TypeVar, Awaitable, Sequence
from io import TextIOWrapper
from inspect import iscoroutinefunction

from .constants import ENCODING


T = TypeVar("T")


class FileWatcher:
    refresh_in_seconds = 0.1
    stamp = 0

    def __init__(self, file_to_watch: Path,
                 file_changed_callback: Callable[..., T],
                 *args, **kwargs):
        self.filename = file_to_watch
        self.__callback = file_changed_callback
        self.__args = args
        self.__kwargs = kwargs

    async def __call(self) -> bool:
        if iscoroutinefunction(self.__callback):
            await self.__callback(*self.__args, **self.__kwargs)
            return True
        elif callable(self.__callback):
            self.__callback(*self.__args, **self.__kwargs)
            return True
        return False

    async def look(self):
        if not self.filename.exists():
            return
        stamp = stat(self.filename).st_mtime
        if stamp == self.stamp:
            return
        self.stamp = stamp
        await self.__call()

    async def watch(self) -> None:
        while True:
            await self.look()
            await sleep(self.refresh_in_seconds)

    async def async_look(self) -> None:
        while True:
            if not self.filename.exists():
                await sleep(self.refresh_in_seconds)
                continue
            stamp = stat(self.filename).st_mtime
            if stamp == self.stamp:
                await sleep(self.refresh_in_seconds)
                continue
            self.stamp = stamp
            called = await self.__call()
            if called:
                return
            else:
                msg = "FileWatcher's callback must be callable or " + \
                      f"awaitable, not {type(self.__callback)}"
                raise RuntimeError(msg)


class ProcessWatcher:
    refresh_in_seconds = 1
    delay_in_seconds = 1

    def __init__(self, check_function: Callable[..., bool],
                 fun_args: Sequence, tasks: Sequence[Task]):
        self.__tasks = tasks
        self.__check = check_function
        self.__check_args = fun_args

    def __tasks_done(self) -> bool:
        for task in self.__tasks:
            if not task.done():
                return False
        return True

    async def cancel_tasks(self) -> None:
        for task in self.__tasks:
            task.cancel()
        while not self.__tasks_done():
            await sleep(0)

    async def watch(self) -> None:
        max_try_count = \
            self.delay_in_seconds // self.refresh_in_seconds
        try_count = 0
        while True:
            if try_count < max_try_count:
                try_count += 1
                await sleep(self.refresh_in_seconds)
                continue
            if not self.__check(*self.__check_args):
                await self.cancel_tasks()
            await sleep(self.refresh_in_seconds)


class State(Enum):
    COPY = "copy"
    PASTE = "paste"
    DONE = "done"
    NONE = "none"
    HALT = "halt"


def eopen(file: Path, mode: str) -> TextIOWrapper:
    return open(file, mode, encoding=ENCODING, errors="strict")


def check_state(filename: Path) -> State:
    with eopen(filename, "rt") as f:
        data = str(f.read())
        if State.DONE.value in data:
            return State.DONE
        elif State.PASTE.value in data:
            return State.PASTE
        elif State.COPY.value in data:
            return State.COPY
        elif State.HALT.value in data:
            return State.HALT
        return State.NONE


async def run_in_executor(f: Callable[..., T], *args: Any, **kwargs: Any) -> T:
    fn = partial(f, *args, **kwargs)
    return await get_event_loop().run_in_executor(None, fn)


if version_info > (3, 7):
    import asyncio

    def run(co: Awaitable[T]) -> T:
        return asyncio.run(co)

else:

    def run(co: Awaitable[T]) -> T:
        loop = get_event_loop()
        try:
            return loop.run_until_complete(co)
        finally:
            try:
                loop.run_until_complete(loop.shutdown_asyncgens())
            finally:
                loop.close()
