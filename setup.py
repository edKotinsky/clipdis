from setuptools import setup
from setuptools.command.install import install
from setuptools.command.develop import develop
from enum import Enum
from typing import Dict, List
from distutils.errors import DistutilsOptionError as OptionError


HOST_INSTALL_REQUIRES = [
    "pexpect >= 4.8.0",
    "ptyprocess >= 0.7.0",
    "pyperclip >= 1.8.0"
]
CONTAINER_INSTALL_REQUIRES = []

HOST_ENTRY_POINTS = [
    "clipdis_start = clipdis.main:run_main"
]
CONTAINER_ENTRY_POINTS = [
    "c = clipdis.main:run_container",
    "p = clipdis.main:run_container",
    "xclip = clipdis.main:run_container",
    "xsel = clipdis.main:run_container"
]


class ConditionalInstall(object):
    class __Type(Enum):
        NONE = 0
        HOST = 1
        CONTAINER = 2

    def __init__(self):
        self.__type: self.__Type = self.__Type.NONE
        pass

    def set(self, type: str) -> None:
        if type == "host" or type == "":
            self.__type: self.__Type = self.__Type.HOST
        elif type == "container":
            self.__type: self.__Type = self.__Type.CONTAINER
        else:
            raise OptionError(f"Unrecognized `--type` option value: {type}; "
                              "Possible values are: host and container; "
                              "See --help")

    def get_requirements(self) -> List[str]:
        type = self.__type
        if type is self.__Type.HOST:
            return HOST_INSTALL_REQUIRES
        else:
            return CONTAINER_INSTALL_REQUIRES

    def get_entry_points(self) -> Dict[str, List[str]]:
        type = self.__type
        if type is self.__Type.HOST:
            return {"console_scripts": HOST_ENTRY_POINTS}
        else:
            return {"console_scripts": CONTAINER_ENTRY_POINTS}


condinst = ConditionalInstall()


class CommandMixin(object):
    user_options = install.user_options + [
        (
            "type=",
            None,
            "Installation type: is `clipdis` installing on a host or a "
            "container; `--type=(host|container|None)`; "
            "If None, then type is host"
        )
    ]

    def initialize_options(self):
        super().initialize_options()
        self.type = ""

    def finalize_options(self):
        super().finalize_options()

    def run(self):
        condinst.set(self.type)
        super().run()


class InstallCommand(CommandMixin, install):
    user_options = install.user_options + CommandMixin.user_options


class DevelopCommand(CommandMixin, develop):
    user_options = develop.user_options + CommandMixin.user_options


setup(
    name="clipdis",
    version="0.0.1",
    license="MIT",
    description="Tool for sharing clipboard between host and Docker container",
    author="Gleb Zlatanov",
    url="https://github.com/edKotinsky/clipdis",
    entry_points=condinst.get_entry_points(),
    install_requires=condinst.get_requirements(),
    cmdclass={
        "install": InstallCommand,
        "develop": DevelopCommand
    }
)
