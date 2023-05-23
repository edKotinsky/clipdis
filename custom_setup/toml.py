from typing import Any

INDENT = "    "
SIZE_TO_BREAK = 4


class DumpTOML(object):
    """
    Toy Python to TOML translator, created to do not depend on third-party
    modules.
    It is implemented using recursion, not iteration, so it is not inteded
    to convert big amounts of data.
    """
    max_header_depth = 1

    def __init__(self):
        self.__dest: str = ""
        self.__depth: int = 0

    def dump(self, data: dict) -> str:
        if not isinstance(data, dict):
            raise TypeError(f"data must be a dictionary, not {type(data)}")
        pairs_first = True
        for k, v in data.items():
            if isinstance(v, dict):
                if len(self.__dest):
                    self.__newline()
                self.__header(k)
                self.__dump_dict(v)
                pairs_first = False
            elif pairs_first:
                self.__key_value_pair(k)
                self.__newline()
            else:
                raise ValueError("key-value pairs may be before tables only")
        return self.__dest

    def __dump_dict(self, d: dict) -> None:
        for k, v in d.items():
            if isinstance(v, dict):
                self.__dest += k + '.'
                self.__dump_dict(v)
            else:
                self.__key_value_pair(k, v)
                self.__newline()

    def __key_value_pair(self, key: str, value: Any,
                         indent_lvl: int = 1) -> None:
        if not isinstance(key, str):
            raise TypeError(f"Key must be string, not {type(key)}")
        self.__dest += self.__key_str(key) + " = "
        if isinstance(value, str):
            self.__load_str(value)
        elif isinstance(value, bool):
            if value:
                self.__dest += "true"
            else:
                self.__dest += "false"
        elif isinstance(value, int) or isinstance(value, float):
            self.__dest += str(value)
        elif isinstance(value, dict):
            self.__load_braced_dict(value, indent_lvl)
        elif isinstance(value, list):
            self.__load_list(value, indent_lvl)
        else:
            raise TypeError(f"Value of unexpected type: {value}: {type(value)}")

    def __header(self, name: str) -> None:
        self.__dest += '[' + name + ']\n'

    def __load_braced_dict(self, d: dict, indent_lvl: int) -> None:
        contains_nested_dl = True \
            if any(isinstance(x, dict) or isinstance(x, list) for x in d) \
            else False
        breaklines = len(d) >= SIZE_TO_BREAK or contains_nested_dl
        ws = '\n' if breaklines else ' '
        indent = INDENT * indent_lvl if breaklines else ''
        closing_brace_indent = \
            INDENT * (indent_lvl - 1) if breaklines and indent_lvl > 1 else ''
        self.__dest += '{' + ws

        last = len(d) - 1
        counter = 0
        for k, v in d.items():
            counter += 1
            self.__dest += indent
            self.__key_value_pair(k, v, indent_lvl)
            self.__dest += ',' + ws if counter == last else ws
        self.__dest += closing_brace_indent + '}'

    def __load_list(self, ll: list, indent_lvl: int) -> None:
        contains_nested_dl = True \
            if any(isinstance(x, dict) or isinstance(x, list) for x in ll) \
            else False
        breaklines = len(ll) >= SIZE_TO_BREAK or contains_nested_dl
        ws = '\n' if breaklines else ' '
        indent = INDENT * indent_lvl if breaklines else ''
        closing_brace_indent = \
            INDENT * (indent_lvl - 1) if breaklines and indent_lvl > 1 else ''
        self.__dest += '[' + ws

        for item in ll:
            self.__dest += indent
            if isinstance(item, dict):
                self.__load_braced_dict(item, indent_lvl + 1)
            elif isinstance(item, list):
                self.__load_list(item, indent_lvl + 1)
            elif isinstance(item, str):
                self.__load_str(item)
            self.__dest += ',' + ws
        self.__dest += closing_brace_indent + ']'

    def __load_str(self, s: str) -> None:
        self.__dest += '"' + s + '"'

    def __key_str(self, s: str) -> str:
        if ' ' in s:
            return '"' + s + '"'
        return s

    def __newline(self) -> None:
        self.__dest += '\n'
