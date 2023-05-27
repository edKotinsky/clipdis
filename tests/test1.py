from pathlib import Path
from os import environ
from copy import copy
from shutil import rmtree
import subprocess as sub
import pyperclip as pyc
from sys import stderr
import time


def _inspect(statefile, datafile):
    with open(statefile, "rt") as sf:
        with open(datafile, "rt") as df:
            print(f"Datafile: '{df.read()}', Statefile: '{sf.read()}'")


def test():
    cwd = Path(__file__).resolve().parent.parent
    testdir = cwd / "test-clipboard"

    # remember previous clipboard data to restore it
    clipboard = pyc.paste()
    pyc.copy("")
    try:
        if not testdir.exists():
            testdir.mkdir()

        statefile = testdir / ".state"
        datafile = testdir / ".data"

        # clip tool requires CLIPDIS_DIRECTORY environment variable to be set
        env = copy(environ)
        env["CLIPDIS_DIRECTORY"] = str(testdir)

        clip_cmd = ["python3", "-m", "clipdis.run_clip", "--directory", testdir]
        watcher_cmd = ["python3", "-m", "clipdis.run_watcher", "--dry-run",
                       "-d", testdir]

        copy_cmd = clip_cmd + ["--copy"]
        paste_cmd = clip_cmd + ["--paste"]

        with sub.Popen(watcher_cmd) as watcher:
            data = "hello"
            print(f"Test 1: copying '{data}'")
            sub.run(copy_cmd, input=data, text=True, env=env)
            time.sleep(0.1)
            result = pyc.paste()
            if result != data:
                print(f"Failed: expected '{data}', got '{result}'", file=stderr)
                _inspect(statefile, datafile)
                return 1
            else:
                print("Success")

            data = "hello world"
            pyc.copy(data)
            print(f"Test 2: pasting '{data}'")
            proc = sub.run(paste_cmd, stdout=sub.PIPE, stderr=sub.STDOUT,
                           text=True, env=env)
            result = proc.stdout
            if result != data:
                print(f"Failed: expected '{data}', got '{result}'", file=stderr)
                _inspect(statefile, datafile)
                return 1
            else:
                print("Success")

            print("Test 3: halt watcher")
            with open(testdir / ".state", "wt") as sf:
                sf.write("halt")
            time.sleep(0.1)
            if watcher.poll() is None:
                print("Failed: watcher not exited", file=stderr)
                _inspect(statefile, datafile)
                return 1
            elif watcher.poll() != 0:
                print("Failed: watcher exited with error", file=stderr)
                print(f"Return code: {watcher.returncode}, "
                      "Info: {watcher.stderr}")
                return 1
            else:
                print("Success")

    finally:
        rmtree(testdir)
        pyc.copy(clipboard)


if __name__ == "__main__":
    exit(test())
