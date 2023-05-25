import logging
import struct
import termios
import pyperclip as pyc
from os import getcwd, get_terminal_size
from asyncio import CancelledError, Task, sleep, create_task, gather
from pathlib import Path
from typing import Sequence
from shutil import which
from pexpect import spawn
from sys import stdout
from fcntl import ioctl
from signal import signal, SIGWINCH
from argparse import ArgumentParser, Namespace

from .common import FileWatcher, State, eopen, check_state
from .constants import STATEFILE, DATAFILE


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
    except Exception as err:
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
                 user_name: str, image: str, container_name: str,
                 dry_run: bool, logfile: str):
        opts = dry_run or data_directory and user_name and image and \
            container_name
        if not (clip_directory and opts):
            raise RuntimeWarning(
                "Not all necessary arguments are specified. Type `--help`")
        self.datadir = data_directory
        self.clipdir = clip_directory
        self.user = user_name
        self.image = image
        self.name = container_name
        self.logfile = logfile
        self.dryrun = dry_run


def _tasks_done(tasks: Sequence[Task]) -> bool:
    for task in tasks:
        if not task.done():
            return False
    return True


async def _cancel_tasks(tasks: Sequence[Task]) -> None:
    for task in tasks:
        task.cancel()
    while not _tasks_done(tasks):
        await sleep(0)


async def _interact(data: Namespace, tasks: Sequence[Task]) -> None:
    class SigWinChHandler:
        def __init__(self, proc: spawn):
            self.proc = proc

        def handle(self, sig, frame):
            s = struct.pack("HHHH", 0, 0, 0, 0)
            a = struct.unpack('hhhh', ioctl(stdout.fileno(),
                              termios.TIOCGWINSZ, s))
            if not self.proc.closed:
                self.proc.setwinsize(a[0], a[1])

    internal_data = f"{data.datadir}:/home/{data.user}/.data"
    workdir = f"/home/{data.user}/data"
    workdir_volume = f"{getcwd()}:{workdir}"

    args = ["run", "--interactive", "--tty", "--rm",
            "--name", data.containername,
            "--volume", internal_data,
            "--volume", workdir_volume,
            "--workdir", workdir,
            data.image, "/bin/bash"]

    # TODO: find a cross-platform alternative to pexpect.spawn
    # See https://pexpect.readthedocs.io/en/stable/overview.html#windows
    sz = get_terminal_size()
    p = spawn("docker", args=args, dimensions=(sz[1], sz[0]))
    winch_handler = SigWinChHandler(p)
    signal(SIGWINCH, winch_handler.handle)
    p.interact(escape_character=None)

    await _cancel_tasks(tasks)


async def _halt(statefile: Path, tasks: Sequence[Task]) -> None:
    while True:
        if not statefile.exists():
            await _cancel_tasks(tasks)
        with eopen(statefile, "rt") as sf:
            state = sf.read()
            if State.HALT.value in state:
                await _cancel_tasks(tasks)
                return
            await sleep(0.1)
    pass


async def watcher() -> None:
    parser = ArgumentParser()

    parser.add_argument("-d", "--datadir", type=str, required=True,
                        help="Directory where the container will store"
                        "its internal data")
    parser.add_argument("-c", "--clipdir", type=str, required=True,
                        help="Directory where the clipboard dispatcher "
                        "files will be stored; in this directory the "
                        "docker's volume will be mounted")
    parser.add_argument("-u", "--user", type=str, required=True,
                        help="Username")
    parser.add_argument("-i", "--image", type=str, required=True,
                        help="Image name")
    parser.add_argument("-n", "--containername", type=str,
                        default="hello_world",
                        help="Container name; by default: hello_world")
    parser.add_argument("-l", "--logfile", type=str, default='_',
                        help="File to write log messages")
    parser.add_argument("--dry-run", action='store_true',
                        help="Do not start docker container; in this "
                        "mode options --datadir, --user, --image, "
                        "--containername have no effect and are "
                        "unnecessary;")
    ns = parser.parse_args()

    _configure_logger(ns.logfile)

    if not which("docker"):
        raise RuntimeWarning("docker is not found")

    tasks = set()

    statefile = Path(ns.clipdir) / STATEFILE
    datafile = Path(ns.clipdir) / DATAFILE

    tasks.add(create_task(_halt(statefile, tasks)))

    watcher = FileWatcher(statefile, _callback, statefile, datafile, tasks)
    tasks.add(create_task(watcher.watch()))

    if not ns.dry_run:
        tasks.add(create_task(_interact(ns, tasks)))

    try:
        await gather(*tasks)
    except CancelledError:
        pass
