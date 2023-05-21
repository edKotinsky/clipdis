from argparse import ArgumentParser

from .common import run
from .clip import clipboard_tool
from .start_docker import InteractData, start


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
                                 logfile=ns.logfile)
            await start(idata)
        return 0
    except Exception as err:
        print(f"Error: {err}")
        return 1


run(main())
