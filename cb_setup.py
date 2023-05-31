from custom_setup import Py2TOML
from argparse import ArgumentParser
from subprocess import Popen, PIPE, STDOUT
from sys import stdout, exit
from pathlib import Path

config = {
    "build-system": {
        "requires": ["setuptools"],
        "build-backend": "setuptools.build_meta"
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
        "dependencies": [
            "pyperclip >= 1.8.0"
        ],
    },
    "tool.setuptools.packages.find": {
        "where": ["src"],
        "include": ["clipdis"],
        "namespaces": False
    }
}

HOST_SCRIPTS = {
    "clipdis_run": "clipdis.run_watcher:run"
}

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
    parser.add_argument("--pip-args", type=str, default='',
                        help="Arguments that will be passed to pip")
    parser.add_argument("-d", "--debug", action="store_true",
                        help="Print generated pyproject.toml contents")
    ns = parser.parse_args()

    if ns.install == "host":
        config["project"]["scripts"] = HOST_SCRIPTS
    else:
        config["project"]["scripts"] = CONTAINER_SCRIPTS

    toml = Py2TOML()
    s = toml.convert(config)

    if ns.debug:
        print(s)

    if ns.dry_run:
        print(s)
        return 0

    with open("pyproject.toml", "wt") as f:
        f.write(s)

    if ns.no_install:
        return 0

    cmd = ["pip", "install"] + ns.pip_args.split()
    if ns.develop:
        cmd.append("-e")
    cmd.append(".")

    proc = Popen(cmd, stdout=PIPE, stderr=STDOUT, text=True,
                 cwd=Path(__file__).parent.resolve())
    while True:
        data = proc.stdout.readline()
        if not data:
            break
        stdout.write(data)
        stdout.flush()

    return proc.poll()


exit(main())
