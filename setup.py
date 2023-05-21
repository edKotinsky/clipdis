from setuptools import setup
from setuptools.command.install import install


class InstallCommand(install):
    user_options = install.user_options + [
        ("type=", None, None)
    ]

    def initialize_options(self):
        install.initialize_options(self)
        self.type = None

    def finalize_options(self):
        install.finalize_options(self)

    def run(self):
        global installation_type
        installation_type = self.type
        install.run(self)


setup(
    name="clipdis",
    version="0.0.1",
    license="MIT",
    description="Tool for sharing clipboard between host and Docker container",
    author="Gleb Zlatanov",
    url="https://github.com/edKotinsky/clipdis",
    entry_points={
        "console_scripts": [
            "clipdis_start = clipdis.main:run_main"
        ]
    },
    install_requires=[
        "pexpect >= 4.8.0",
        "ptyprocess >= 0.7.0",
        "pyperclip >= 1.8.0"
    ],
    cmdclass={
        "install": InstallCommand
    }
)
