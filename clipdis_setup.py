from custom_setup import Py2TOML
from argparse import ArgumentParser
from subprocess import Popen, PIPE, STDOUT
from sys import stdout, exit
from pathlib import Path

cwd = Path(__file__).resolve().parent

config = {
    "build-system": {
        "requires": ["setuptools"]
    },
    "project": {
        "name": "clipdis",
        "version": "0.0.1",
        "authors": [
            {"name": "Gleb Zlatanov"}
        ],
        "description": "Utility for sharing clipboard to Docker container",
        "requires-python": ">=3.7",
        "license": {
            "text": "MIT"
        },
        "urls": {
            "Repository": "https://github.com/edKotinsky/clipdis"
        },
        "classifiers": [],
        "dependencies": [],
        "dynamic": [],
        "scripts": {}
    },
    "tool.setuptools.packages.find": {
        "where": str(cwd),
        "include": ["clipdis"]
    }
}

HOST_DEPENDENCIES = [
    "pyperclip >= 1.8.0"
]

HOST_SCRIPTS = {
    "clipdis_run": "clipdis.run_watcher:run"
}

CONTAINER_DEPENDENCIES = []

CONTAINER_SCRIPTS = {
    "c": "clipdis.run_clip:run",
    "pbcopy": "clipdis.run_clip:run",
    "xclip": "clipdis.run_clip:run",
    "xsel": "clipdis.run_clip:run",
    "wl-copy": "clipdis.run_clip:run",
    "p": "clipdis.run_clip:run",
    "pbpaste": "clipdis.run_clip:run",
    "wl-paste": "clipdis.run_clip:run"
}


def main() -> int:
    parser = ArgumentParser()
    parser.add_argument("-i", "--install", type=str, required=True,
                        choices=("host", "container"),
                        help="Either installation processes on a host or in "
                        "a container")
    parser.add_argument("--dry-run", action="store_true",
                        help="Do not create pyproject.toml and run "
                        "`pip install`, just print the output and exit")
    parser.add_argument("-e", "--develop", action="store_true",
                        help="Install in develop mode")
    parser.add_argument("-g", "--no-install", action="store_true",
                        help="Generate pyproject.toml without installation")
    ns = parser.parse_args()

    if ns.install == "host":
        config["project"]["dependencies"] = HOST_DEPENDENCIES
        config["project"]["scripts"] = HOST_SCRIPTS
    else:
        config["project"]["dependencies"] = CONTAINER_DEPENDENCIES
        config["project"]["scripts"] = CONTAINER_SCRIPTS

    toml = Py2TOML()
    s = toml.convert(config)

    if ns.dry_run:
        print(s)
        return 0

    with open("pyproject.toml", "wt") as f:
        f.write(s)

    if ns.no_install:
        return 0

    cmd = ["pip", "install"]
    if ns.develop:
        cmd.append("-e")
    cmd.append(".")

    proc = Popen(cmd, stdout=PIPE, stderr=STDOUT, text=True)
    while True:
        data = proc.stdout.readline()
        if not data:
            break
        stdout.write(data)
        stdout.flush()

    return proc.poll()


exit(main())
