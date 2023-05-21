from typing import Sequence
from sys import stdin, stdout
from pathlib import Path
from os import stat

from .common import run_in_executor, eopen, State, FileWatcher
from .constants import STATEFILE, DATAFILE, ENCODING


def _is_copy(name: str, args: Sequence[str]) -> bool:
    if name in {"c", "pbcopy", "wl-copy"}:
        return True
    elif name == "xclip" and {*args}.isdisjoint({"-o", "-out"}):
        return True
    elif name == "xsel" and {*args}.isdisjoint({"-o", "--output"}):
        return True
    else:
        return False


def _is_paste(name: str, args: Sequence[str]) -> bool:
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
            msg = "State file is not in proper condition, must be DONE"
            raise RuntimeError(msg)
    with eopen(datafile, "rt") as df:
        data = df.read()
        stdout.write(data)
        stdout.flush()


async def _paste(datafile: Path, statefile: Path) -> None:
    sf_watcher = FileWatcher(statefile, _paste_callback, datafile, statefile)
    with eopen(statefile, "wt") as sf:
        sf.write(State.PASTE.value)
        sf_watcher.stamp = stat(statefile).st_mtime
    await sf_watcher.async_look()


async def clipboard_tool(binname: str, directory: str,
                         args: Sequence[str]) -> None:
    datafile = directory / DATAFILE
    statefile = directory / STATEFILE

    if not datafile.exists():
        datafile.touch()
    if not statefile.exists():
        statefile.touch()

    binname = Path(binname).stem

    if _is_copy(binname, args):
        await _copy(datafile, statefile)
    elif _is_paste(binname, args):
        await _paste(datafile, statefile)
    else:
        raise RuntimeError(f"Unrecognized program name: {binname}")
