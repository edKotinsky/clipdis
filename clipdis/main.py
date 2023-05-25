from traceback import format_exc

from .clip import clipboard_tool
from .watcher import watcher
from enum import Enum


class ClipdisType(Enum):
    WATCHER = 0
    CLIP = 1


async def main(type: ClipdisType) -> int:
    try:
        if type is ClipdisType.WATCHER:
            await watcher()
        else:
            await clipboard_tool()
        return 0
    except RuntimeWarning as err:
        print(f"Warning: {err}")
    except Exception as err:
        print(f"Error: {err}")
        trace: str = format_exc(chain=False)
        print("Where:")
        _print_stacktrace(trace)
        return 1


def _print_stacktrace(trace: str) -> None:
    trace: list[str] = trace.split(sep='\n')
    for i in range(len(trace)):
        line = trace[i]
        if "clipdis/" in line:
            print(line)
            if i + 1 < len(trace):
                print(trace[i + 1])
