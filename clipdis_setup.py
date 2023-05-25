from custom_setup.toml import DumpTOML
from argparse import ArgumentParser
from subprocess import Popen, PIPE, STDOUT
from sys import stdout, exit

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
    "tool.setuptools": {
        "packages": ["clipdis"]
    }
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
    ns = parser.parse_args()

    if ns.install == "host":
        config["project"]["dependencies"] = [
            "pexpect >= 4.8.0",
            "ptyprocess >= 0.7.0",
            "pyperclip >= 1.8.0"
        ]
        config["project"]["scripts"] = {
            "clipdis_start": "clipdis.run_watcher:run"
        }
    else:
        config["project"]["dependencies"] = []
        config["project"]["scripts"] = {
            "c": "clipdis.run_clip:run",
            "pbcopy": "clipdis.run_clip:run",
            "xclip": "clipdis.run_clip:run",
            "xsel": "clipdis.run_clip:run",
            "wl-copy": "clipdis.run_clip:run",
            "p": "clipdis.run_clip:run",
            "pbpaste": "clipdis.run_clip:run",
            "wl-paste": "clipdis.run_clip:run"
        }

    d = DumpTOML()
    s = d.dump(config)

    if ns.dry_run:
        print(s)
        return 0

    with open("pyproject.toml", "wt") as f:
        f.write(s)

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
