from pathlib import Path

TOP_LEVEL = Path(__file__).resolve().parent.parent
BIN_DIR = TOP_LEVEL / "bin"
CB_DIR = TOP_LEVEL / "cb"

ENCODING = "utf-8"
STATEFILE = Path(".state")
DATAFILE = Path(".data")
