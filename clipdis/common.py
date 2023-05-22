from sys import version_info
from pathlib import Path
from os import stat
from asyncio import sleep, get_event_loop
from functools import partial
from enum import Enum
from typing import Any, Callable, TypeVar, Awaitable
from io import TextIOWrapper
from inspect import iscoroutinefunction

from .constants import ENCODING


T = TypeVar("T")


class FileWatcher:
    refresh_in_seconds = 0.1
    stamp = 0

    def __init__(self, file_to_watch: Path, file_changed_callback,
                 *args, **kwargs):
        self.filename = file_to_watch
        self.__callback = file_changed_callback
        self.__args = args
        self.__kwargs = kwargs

    def look(self) -> None:
        if not self.filename.exists():
            return
        stamp = stat(self.filename).st_mtime
        if stamp == self.stamp:
            return
        self.stamp = stamp
        if not callable(self.__callback):
            msg = "FileWatcher's callback must be callable, not " + \
                  type(self.__callback)
            raise RuntimeError(msg)
        self.__callback(*self.__args, **self.__kwargs)

    async def watch(self) -> None:
        while True:
            self.look()
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
            if iscoroutinefunction(self.__callback):
                await self.__callback(*self.__args, **self.__kwargs)
                return
            elif callable(self.__callback):
                self.__callback(*self.__args, **self.__kwargs)
                return
            else:
                msg = "FileWatcher's callback must be callable or " + \
                      f"awaitable, not {type(self.__callback)}"
                raise RuntimeError(msg)


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
            return State.NONE
        for s in State:
            if s.value in data:
                return s
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
