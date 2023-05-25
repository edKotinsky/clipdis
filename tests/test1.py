from pathlib import Path
from os import environ
from copy import copy
from typing import Mapping


def test1():
    cwd = Path.cwd()

    testdir = cwd / "test-clipboard"
    if not testdir.exists():
        testdir.mkdir()

    env: Mapping = copy(environ)
    env["CLIPDIS_DIRECTORY"] = testdir

    clip_cmd = ["python3", "-m", "clipdis.run_clip"]
