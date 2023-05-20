from argparse import ArgumentParser

from .common import run
from .clip import clipboard_tool
from .watcher import watcher


parser = ArgumentParser()
parser.add_argument("--directory", type=str, required=True,
                    help="Docker volume directory")
parser.add_argument("--logfile", type=str, default='_',
                    help="File to write log messages")
group = parser.add_mutually_exclusive_group(required=True)
group.add_argument("--id", type=str)
group.add_argument("--name", type=str)

ns, args = parser.parse_known_args()


# Utility name is required only by container's clipboard side
# Container id is required by the host side
async def main() -> int:
    try:
        if ns.name:
            await clipboard_tool(ns.name, ns.directory, args)
        elif ns.id:
            await watcher(ns.id, ns.directory, ns.logfile)
        return 0
    except Exception as err:
        print(err)
        return 1


run(main())
