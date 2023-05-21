import logging
import pyperclip as pyc
from os import getcwd
from asyncio import CancelledError, sleep, create_task, gather
from pathlib import Path
from typing import Sequence, Awaitable
from pexpect import spawn

from .common import FileWatcher, State, eopen, check_state
from .constants import STATEFILE, DATAFILE

MODULE = "cb.watcher"


def _configure_logger(logfile: str):
    if logfile == '_':
        return
    name = "clipboard-watcher"
    logging.basicConfig(filename=logfile,
                        level=logging.INFO,
                        format=f"%(asctime)s {name} %(levelname)s: %(message)s",
                        datefmt="%Y-%m-%d %H:%M:%S")
    logging.info("Logging initialized")


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


def _callback(statefile: Path, datafile: Path, tasks: set) -> None:
    state = check_state(statefile)
    if state != State.NONE:
        logging.info(f"State changed: {state.value}")
        if state == State.COPY:
            _copy(datafile)
        elif state == State.PASTE:
            _paste(datafile, statefile)


class InteractData(object):
    def __init__(self, data_directory: str, clip_directory: str,
                 user_name: str, image: str, container_name: str, logfile: str):
        if not data_directory:
            raise RuntimeError(
                "Not all necessary arguments are specified. Type `--help`")
        self.datadir = data_directory
        self.clipdir = clip_directory
        self.user = user_name
        self.image = image
        self.name = container_name
        self.logfile = logfile


def _tasks_done(tasks: Sequence[Awaitable]) -> bool:
    for task in tasks:
        if not task.done():
            return False
    return True


async def _cancel_tasks(tasks: Sequence[Awaitable]) -> None:
    for task in tasks:
        task.cancel()
    while not _tasks_done(tasks):
        await sleep(0)


async def _interact(data: InteractData, tasks: Sequence[Awaitable]) -> None:
    internal_data = f"{data.datadir}:/home/{data.user}/.data"
    workdir = f"/home/{data.user}/data"
    workdir_volume = f"{getcwd()}:{workdir}"

    args = ["run", "--interactive", "--tty", "--rm",
            "--name", data.name,
            "--volume", internal_data,
            "--volume", workdir_volume,
            "--workdir", workdir,
            data.image, "/bin/bash"]

    # TODO: find a cross-platform alternative to pexpect.spawn
    # See https://pexpect.readthedocs.io/en/stable/overview.html#windows
    p = spawn("docker", args=args)
    p.interact(escape_character=None)

    await _cancel_tasks(tasks)


async def start(data: InteractData) -> None:
    _configure_logger(data.logfile)

    tasks = set()

    statefile = Path(data.clipdir) / STATEFILE
    datafile = Path(data.clipdir) / DATAFILE

    watcher = FileWatcher(statefile, _callback, statefile, datafile, tasks)
    tasks.add(create_task(watcher.watch()))

    tasks.add(create_task(_interact(data, tasks)))

    try:
        await gather(*tasks)
    except CancelledError:
        pass
