import logging
import pyperclip as pyc
import subprocess as sub

from asyncio import CancelledError, sleep, create_task, gather
from pathlib import Path
from typing import Sequence, Awaitable, Callable, TypeVar
from argparse import ArgumentParser
from multiprocessing import Process, current_process
from os import execvp
from functools import partial
from shutil import which

from .common import FileWatcher, ProcessWatcher, State, eopen, check_state, run
from .constants import STATEFILE, DATAFILE

LOCKFILE = ".lock"
DETACHED_PROCESS_NAME = "clipdis-watcher"


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


async def watcher() -> None:
    if not which("docker"):
        raise RuntimeWarning("docker is not found")

    parser = ArgumentParser()

    parser.add_argument("-D", "--cvolume", type=str,
                        help="Directory where the volume will be mounted in a "
                        "container")
    parser.add_argument("-d", "--hvolume", type=str, required=True,
                        help="Directory where the volume will be mounted on a "
                        "host")
    parser.add_argument("-n", "--containername", type=str,
                        default="hello_world",
                        help="Container name; by default: hello_world")
    parser.add_argument("-l", "--logfile", type=str, default='_',
                        help="File to write log messages; disables logging, "
                        "when not specified")
    parser.add_argument("--dry-run", action='store_true',
                        help="Do not start docker container; in this "
                        "mode options --datadir, --user, --image, "
                        "--containername have no effect and are "
                        "unnecessary;")
    ns, args = parser.parse_known_args()

    if not (ns.dry_run or ns.cvolume and ns.hvolume):
        parser.print_usage()
        raise RuntimeWarning("Specify volume directories or run with --dry-run")

    # spawn detached watcher
    co_runner = partial(_run_co, _main,
                        (ns.hvolume, ns.containername, ns.logfile, ns.dry_run))
    await _spawn_detached(co_runner)

    if ns.dry_run:
        return

    if _check_container(ns.containername):
        print("Container is already spawned")
        exec_start_attach_container(ns.containername)

    docker_cmd = ["docker", "run", "--interactive", "--tty",
                  "--name", ns.containername,
                  "--volume", f"{ns.hvolume}:{ns.cvolume}",
                  *args]

    execvp("docker", docker_cmd)


async def _callback(statefile: Path, datafile: Path,
                    process_watcher: ProcessWatcher) -> None:
    state = check_state(statefile)
    if state != State.NONE:
        logging.info(f"State changed: {state.value}")
        if state == State.COPY:
            _copy(datafile)
        elif state == State.PASTE:
            _paste(datafile, statefile)
        elif state == State.HALT:
            await process_watcher.cancel_tasks()


def _check_container(name: str, statefile: Path = "",
                     dry_run: bool = True) -> bool:
    if not (dry_run or statefile.exists()):
        return False
    cmd = ["docker", "container", "ls",
           "--all",
           "--filter", "name=" + name]
    proc = sub.run(cmd, stdout=sub.PIPE, stderr=sub.PIPE, text=True)
    if name not in proc.stdout:
        return False
    return True


async def _main(dir: str, containername: str, logfile: str,
                dry_run: bool) -> None:
    dir = Path(dir)
    lockfile = dir / LOCKFILE

    try:
        if lockfile.exists() or current_process().name != DETACHED_PROCESS_NAME:
            return
        lockfile.touch()

        _configure_logger(logfile)

        tasks = set()

        statefile = dir / STATEFILE
        datafile = dir / DATAFILE

        container_watcher = \
            ProcessWatcher(_check_container,
                           (containername, statefile, dry_run), tasks)

        watcher = FileWatcher(statefile, _callback, statefile, datafile,
                              container_watcher)
        tasks.add(create_task(watcher.watch()))

        if not dry_run:
            tasks.add(create_task(container_watcher.watch()))

        await gather(*tasks)
    except CancelledError:
        pass
    finally:
        lockfile.unlink(missing_ok=True)


# utilities


def exec_start_attach_container(name: str) -> None:
    cmd = ["docker", "start", "-ai", name]
    execvp("docker", cmd)


def _configure_logger(logfile: str):
    if logfile == '_':
        return
    name = "clipboard-watcher"
    logging.basicConfig(filename=logfile,
                        level=logging.INFO,
                        format=f"%(asctime)s {name} %(levelname)s: %(message)s",
                        datefmt="%Y-%m-%d %H:%M:%S")
    logging.info("Logging initialized")


async def _spawn_detached(co: Awaitable):
    # creates detached (orphaned) process by double forking it
    p = _spawn_detached_impl(0, co)
    await sleep(0.1)
    if isinstance(p, Process):
        p.terminate()


def _spawn_detached_impl(count: int, co: Awaitable):
    count += 1
    if count < 2:
        name = DETACHED_PROCESS_NAME + ".fork"
    elif count == 2:
        name = DETACHED_PROCESS_NAME
    else:
        return co()

    p = Process(name=name, target=_spawn_detached_impl, args=(count, co),
                daemon=False)
    p.start()
    return p


_T = TypeVar("_T")


def _run_co(co_func: Callable[..., Awaitable[_T]], args: Sequence) -> _T:
    return run(co_func(*args))
