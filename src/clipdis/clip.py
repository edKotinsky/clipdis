from typing import Sequence
from sys import stdin, stdout, argv
from pathlib import Path
from os import stat
from asyncio import sleep
from argparse import ArgumentParser, Namespace
from os import environ
from .constants import CB_DIR_VAR_NAME

from .common import run_in_executor, eopen, State, FileWatcher
from .constants import STATEFILE, DATAFILE, ENCODING


_wait_refresh_sec = 0.1
_wait_max_time_sec = 1
_wait_max_try = _wait_max_time_sec // _wait_refresh_sec


def _is_copy(name: str, ns: Namespace, args: Sequence[str]) -> bool:
    if name == "run_clip" and ns.copy:
        return True
    if name in {"c", "pbcopy", "wl-copy"}:
        return True
    elif name == "xclip" and {*args}.isdisjoint({"-o", "-out"}):
        return True
    elif name == "xsel" and {*args}.isdisjoint({"-o", "--output"}):
        return True
    else:
        return False


def _is_paste(name: str, ns: Namespace, args: Sequence[str]) -> bool:
    if name == "run_clip" and ns.paste:
        return True
    if name in {"p", "pbpaste", "wl-paste"}:
        return True
    elif name == "xclip" and not {*args}.isdisjoint({"-o", "-out"}):
        return True
    elif name == "xsel" and not {*args}.isdisjoint({"-o", "--output"}):
        return True
    else:
        return False


async def _copy(datafile: Path, statefile: Path) -> None:
    with eopen(datafile, "wt") as df:
        data = await run_in_executor(stdin.buffer.read)
        df.write(data.decode(encoding=ENCODING, errors="strict"))
        with eopen(statefile, "wt") as sf:
            sf.write(State.COPY.value)


def _paste_callback(datafile: Path, statefile: Path) -> None:
    with eopen(statefile, "rt") as sf:
        state = sf.read()
        if State.DONE.value not in state:
            raise RuntimeWarning(
                "State file is not in proper condition, must be DONE")
    with eopen(datafile, "rt") as df:
        data = df.read()
        stdout.write(data)
        stdout.flush()


async def _wait_for_done(statefile: Path) -> bool:
    stamp = 0
    count = 0
    while True:
        if count == _wait_max_try:
            return False
        count += 1
        await sleep(_wait_refresh_sec)
        newstamp = stat(statefile).st_mtime
        if newstamp == stamp:
            continue
        stamp = newstamp
        with eopen(statefile, "rt") as sf:
            if State.DONE.value in sf.read():
                return True


async def _paste(datafile: Path, statefile: Path) -> None:
    sf_watcher = FileWatcher(statefile, _paste_callback, datafile, statefile)
    with eopen(statefile, "wt") as sf:
        sf.write(State.PASTE.value)
    done = await _wait_for_done(statefile)
    if not done:
        return
    await sf_watcher.async_look()


async def clipboard_tool() -> None:
    parser = ArgumentParser()
    binname = Path(argv[0]).stem

    if binname == "run_clip":
        parser.add_argument("--copy", action="store_true")
        parser.add_argument("--paste", action="store_true")
        parser.add_argument("--directory", type=str, required=True)

        ns = parser.parse_args()
        args = []

        directory = ns.directory
    else:
        _, args = parser.parse_known_args()

        if CB_DIR_VAR_NAME not in environ:
            raise RuntimeWarning(f"{CB_DIR_VAR_NAME} variable is not set")
        directory = environ[CB_DIR_VAR_NAME]

    datafile, statefile = _ensure_files(directory)

    if not datafile.exists():
        datafile.touch()
    if not statefile.exists():
        statefile.touch()

    if _is_copy(binname, ns, args):
        await _copy(datafile, statefile)
    elif _is_paste(binname, ns, args):
        await _paste(datafile, statefile)
    else:
        parser.print_usage()
        raise RuntimeWarning(f"Unrecognized program name: {binname}")


def _ensure_files(directory: Path) -> tuple[Path, Path]:
    datafile = directory / DATAFILE
    statefile = directory / STATEFILE

    if not datafile.exists():
        datafile.touch()
    if not statefile.exists():
        statefile.touch()

    return (datafile, statefile)
