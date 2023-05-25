from .main import ClipdisType, main
from .common import run as _run
from sys import exit


def run() -> int:
    exit(_run(main(ClipdisType.WATCHER)))


if __name__ == "__main__":
    run()
