from argparse import ArgumentParser
from traceback import format_exc
from sys import argv
from pathlib import Path
from os import environ

from .clip import clipboard_tool
from .watcher import InteractData, start
from .constants import CB_DIR_VAR_NAME
from enum import Enum


class ClipdisType(Enum):
    WATCHER = 0
    CLIP = 1


async def main(type: ClipdisType) -> int:
    try:
        if type is ClipdisType.WATCHER:
            parser = ArgumentParser()

            parser.add_argument("-d", "--datadir", type=str,
                                help="Directory where the container will store"
                                "its internal data")
            parser.add_argument("-c", "--clipdir", type=str,
                                help="Directory where the clipboard dispatcher "
                                "files will be stored; in this directory the "
                                "docker's volume will be mounted")
            parser.add_argument("-u", "--user", type=str, help="Username")
            parser.add_argument("-i", "--image", type=str, help="Image name")
            parser.add_argument("-n", "--containername", type=str,
                                default="workspace",
                                help="Container name; by default: workspace")
            parser.add_argument("-l", "--logfile", type=str, default='_',
                                help="File to write log messages")
            parser.add_argument("--dry-run", action='store_true',
                                help="Do not start docker container; in this "
                                "mode options --datadir, --user, --image, "
                                "--containername have no effect and are "
                                "unnecessary;")
            ns, args = parser.parse_known_args()
            idata = InteractData(data_directory=ns.datadir,
                                 clip_directory=ns.clipdir,
                                 user_name=ns.user,
                                 image=ns.image,
                                 container_name=ns.containername,
                                 logfile=ns.logfile,
                                 dry_run=ns.dry_run)
            await start(idata)
        else:
            name = Path(argv[0]).stem
            if CB_DIR_VAR_NAME not in environ:
                raise RuntimeWarning(f"{CB_DIR_VAR_NAME} variable is not set")
            directory = environ[CB_DIR_VAR_NAME]
            await clipboard_tool(name, directory, args)
        return 0
    except RuntimeWarning as err:
        print(f"Warning: {err}")
    except Exception as err:
        print(f"Error: {err}")
        trace: str = format_exc(chain=False)
        print("Where:")
        _print_stacktrace(trace)
        return 1


def _print_stacktrace(trace: str) -> None:
    trace: list[str] = trace.split(sep='\n')
    for i in range(len(trace)):
        line = trace[i]
        if "clipdis/" in line:
            print(line)
            if i + 1 < len(trace):
                print(trace[i + 1])
