from argparse import ArgumentParser
from traceback import format_exc
from .clip import clipboard_tool
from .start_docker import InteractData, start
from .common import run


async def main() -> int:
    parser = ArgumentParser()

    clip_args = parser.add_argument_group("clip", "Clip tool args;"
                                          " these arguments only required if"
                                          " module is executed on a container's"
                                          " side")
    clip_args.add_argument("--directory", type=str,
                           help="Docker volume directory")
    clip_args.add_argument("--name", type=str,
                           help="Name of a clipboard tool;"
                           " must be specified only on the container's side")

    watcher = parser.add_argument_group("watcher",
                                        "Args that required by host's side")
    watcher.add_argument("-d", "--datadir", type=str,
                         help="Directory where the container will store its"
                         "internal data")
    watcher.add_argument("-c", "--clipdir", type=str,
                         help="Directory where the clipboard dispatcher files"
                         "will be stored; in this directory the docker's volume"
                         "will be mounted")
    watcher.add_argument("-u", "--user", type=str, help="Username")
    watcher.add_argument("-i", "--image", type=str, help="Image name")
    watcher.add_argument("-n", "--containername", type=str, default="workspace",
                         help="Container name; by default: workspace")
    watcher.add_argument("-l", "--logfile", type=str, default='_',
                         help="File to write log messages")
    watcher.add_argument("--dry-run", action='store_true',
                         help="Do not start docker container; in this mode "
                         "options --datadir, --user, --image, --containername "
                         "have no effect and are unnecessary")

    ns, args = parser.parse_known_args()

    try:
        if ns.name:
            await clipboard_tool(ns.name, ns.directory, args)
        else:
            idata = InteractData(data_directory=ns.datadir,
                                 clip_directory=ns.clipdir,
                                 user_name=ns.user,
                                 image=ns.image,
                                 container_name=ns.containername,
                                 logfile=ns.logfile,
                                 dry_run=ns.dry_run)
            await start(idata)
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


def run_main() -> int:
    return run(main())
