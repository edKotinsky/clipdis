import logging
import subprocess as sub
import pyperclip as pyc
from sys import argv, exit
from asyncio import sleep, create_task, gather, subprocess
from pathlib import Path
from typing import Sequence, Awaitable

from .common import FileWatcher, State, eopen, check_state, run
from .constants import STATEFILE, DATAFILE

MODULE = "cb.watcher"


def _configure_logger(logfile: str):
    if logfile == '_':
        logging.setLevel(logging.CRITICAL)
        return
    name = "clipboard-watcher"
    logging.basicConfig(filename=logfile,
                        level=logging.INFO,
                        format=f"%(asctime)s {name} %(levelname)s: %(message)s",
                        datefmt="%Y-%m-%d %H:%M:%S")
    logging.info("Logging initialized")


class _ContainerChecker:
    refresh_in_seconds = 1

    def __init__(self, container_id: str, tasks: Sequence[Awaitable]):
        self.container_id = container_id
        self.__tasks = tasks
        self.__cmd = ["docker", "container", "ls",
                      "--quiet",
                      "--all",
                      "--filter", "id=" + container_id]

    async def __run(self) -> sub.CompletedProcess:
        return sub.run(self.__cmd,
                       stdout=sub.PIPE, stderr=sub.PIPE, text=True)

    def __tasks_done(self) -> bool:
        for task in self.__tasks:
            if not task.done():
                return False
        return True

    async def __cancel_tasks(self) -> None:
        for task in self.__tasks:
            task.cancel()
        while not self.__tasks_done():
            await sleep(0)

    async def check(self) -> None:
        while True:
            proc = await self.__run()
            if self.container_id not in proc.stdout:
                await self.__cancel_tasks()
                exit(0)
            await sleep(self.refresh_in_seconds)


def _copy(filename: Path) -> None:
    try:
        f = eopen(filename, "rt")
        data = str(f.read())
        pyc.copy(data)
    except pyc.PyperclipException as err:
        logging.error(f"Pyperclip error: {err}")
    except RuntimeError as err:
        logging.error(f"File error: {err}")
        raise
    else:
        logging.info("Copied")
    finally:
        f.close()


def _paste(datafile: Path, statefile: Path) -> None:
    with eopen(datafile, "wt") as f:
        data = pyc.paste()
        f.write(data)
    with eopen(statefile, "wt") as f:
        f.write(State.DONE.value)
    logging.info("Pasted")


def callback(statefile: Path, datafile: Path) -> None:
    state = check_state(statefile)
    if state != State.NONE:
        logging.info(f"State changed: {state.value}")
        if state == State.COPY:
            _copy(datafile)
        elif state == State.PASTE:
            _paste(datafile, statefile)


async def main() -> None:
    argc = len(argv)
    if argc != 4:
        raise RuntimeError(f"""Watcher requires three arguments, provided {argc}:
                           <container-id> <directory> <logfile>""")
    container_id, directory, logfile = argv[1], argv[2], argv[3]

    _configure_logger(logfile)

    tasks = set()

    statefile = Path(directory, STATEFILE)
    datafile = Path(directory, DATAFILE)

    checker = _ContainerChecker(container_id, tasks)
    tasks.add(create_task(checker.check()))

    watcher = FileWatcher(statefile, callback, statefile, datafile)
    tasks.add(create_task(watcher.watch()))

    await gather(*tasks)


async def watcher(container_id: str, directory: str, logfile: str) -> None:
    logfile = Path(logfile)
    if logfile != '_' and not logfile.parent.exists():
        raise RuntimeError(f"Logfile directory {logfile.parent} does not exist")

    cmd = ["python3", "-m", MODULE, container_id, directory, str(logfile)]
    await subprocess.create_subprocess_exec(*cmd)


if __name__ == "__main__":
    run(main())
