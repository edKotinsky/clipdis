from typing import Mapping, List, Tuple, TypeVar, Union
from enum import Enum
from copy import copy
from datetime import datetime


class Py2TOML(object):
    """
    Toy Python to TOML object translator.
    Currently does not support array [[]] notation, only inline arrays.
    """
    INLINE_TABLE_LEFT_BRACE = chr(123)
    INLINE_TABLE_RIGHT_BRACE = chr(125)
    ARRAY_LEFT_BRACE = chr(91)
    ARRAY_RIGHT_BRACE = chr(93)
    eol = '\n'

    def __init__(self, table_heading_lvl: int = 3, indent_size: int = 4,
                 max_block_size: int = 1, table_root: str = "",
                 prefer_inline: Union[bool, int] = True):
        """
        Py2TOML ctor.

        `table_heading_lvl` determines the nesting level, on which headers
        "[key]" will be generated. Indent size is the amount of space
        characters. Max block size determines the length of an inlined struct
        (inline-table or array), for which inlining (placing into one line) is
        allowed.
        """
        self.indent_size = indent_size
        self.indent = ' ' * indent_size
        self.max_block_size = max_block_size
        self.heading_lvl = table_heading_lvl

        assert isinstance(prefer_inline, bool) or \
            isinstance(prefer_inline, int) and prefer_inline > 0
        self.prefer_inline = prefer_inline

    def convert(self, data: Mapping, root: str = "") -> str:
        """
        Converts Python data into TOML.
        `initial` is how the root table will be named. Default: without name.
        """
        try:
            if not root:
                self.heading_lvl += 1
            stack = [([root], data)]
            current_stack = []
            dest = []
            queue = []
            parent_name = []

            # Pop an item from the stack. If an item is a Mapping, then iterate
            # through it. If item[i] is a Mapping, push it into the stack.
            # Otherwise, push key-value pair as a Tuple into a queue.
            # Data in the stack is stored in tuples. First element is the name
            # of a table, second - is the table itself.
            while (len(stack)):
                element = stack.pop()
                if isinstance(element, Tuple):
                    name = element[0]
                    parent_name = name
                    for k, v in element[1].items():
                        if isinstance(v, Mapping):
                            key = copy(parent_name)
                            key.append(k)
                            current_stack.append((key, v))
                        else:
                            self.__push_key_value_pair(k, v, queue)
                    current_stack.reverse()
                    current_stack.append(name)
                    stack += current_stack
                    current_stack = []
                else:
                    queue.append(element)

            # Create a standard table. If item in the queue is a list, then it
            # is a dotted key. Otherwise (it is a tuple), it is a key-value
            # pair.
            T = TypeVar("T", List, Tuple)
            for i in range(len(queue)):
                e: T = queue[i]
                if isinstance(e, List):
                    self.__standard_table(e, stack, dest)
                else:
                    stack.append(self.__value(e))
            return ''.join(dest)
        finally:
            if not root:
                self.heading_lvl -= 1

    # Internal functions

    def __push_key_value_pair(self, key, value, dest: list) -> None:
        if not isinstance(value, List):
            dest.append((key, value))
        else:
            dest.append((key, self.__Array(self.__list(value))))

    def __standard_table(self, ll: List, stack: List, dest: List) -> None:
        """
        Create a standard table. If length of a key with parent table names
        less or equal to heading level, then create a header (see std-table in
        toml.abnf). Otherwise, create a key-value pair.
        """
        if len(ll) <= self.heading_lvl:
            self.__header(ll, dest)
        self.__remove_first(self.heading_lvl, ll)
        parents = self.__dotted_key(ll)
        while len(stack):
            kvp = stack.pop()
            dest.append(self.__concat_entry(parents, kvp))

    def __header(self, ll, dest: list) -> None:
        s = self.__dotted_key(ll)
        if len(dest):
            dest.append(self.eol)
        if len(s):
            dest.append(f"[{s}]{self.eol}")

    def __remove_first(self, n: int, ll: List) -> None:
        for i in range(n):
            if not len(ll):
                return
            ll.pop(0)

    def __dotted_key(self, ll: List) -> str:
        """Concatenates keys through a dot"""
        _str = self.__key
        last = len(ll) - 1
        s = ''
        for i in range(len(ll)):
            s = s + _str(ll[i]) + ('.' if i < last and ll[i] else '')
        return s

    def __concat_entry(self, name: str, kvp: str) -> str:
        """Concatenates previous dotted keys with the key-value pair."""
        return f"{name}{'.' if name else ''}{kvp}"

    class __Array(object):
        """
        Indicates inline struct. See __push_key_value_pair, if the value is
        returned by __list, it is wrapped in __Array.
        This is to avoid quoting value due to space characters in it.
        """

        def __init__(self, s: str):
            self.value = s

    def __value(self, v, indent: str = '', end: str = eol) -> str:
        """__value incapsulates both key-value pairs and array value."""
        if isinstance(v, Tuple):
            value = v[1]
            if isinstance(value, self.__Array):
                value = value.value
                return f"{indent}{self.__key(v[0])} = {value}{end}"
            return f"{indent}{self.__key(v[0])} = {self.__val(value)}{end}"
        else:
            return f"{indent}{self.__val(v)}{end}"

    def __val(self, v):
        if isinstance(v, bool):
            return "true" if v else "false"
        if isinstance(v, str):
            return f'"{v}"' if v.isascii() else f"'{v}'"
        if isinstance(v, int) or isinstance(v, float):
            return str(v)
        if isinstance(v, datetime):
            return v.isoformat()
        raise TypeError(f"Type '{type(v)}' not handled yet: '{v}'")

    def __key(self, k) -> str:
        if isinstance(k, bool):
            return "true" if k else "false"
        if isinstance(k, str):
            if ' ' in k:
                return f'"{k}"' if k.isascii() else f"'{k}'"
            return k
        if isinstance(k, int):
            return str(k)
        raise TypeError(f"Type '{type(k)}' is not allowed for a key: '{k}'")

    class _Entry(object):
        """
        _Entry class representates braces in inlined tables. It carries
        important info about a block (block is a table body, all which is
        between braces), such as: block name, block size (len) and acts as a
        brace: it indicates opening and closing of a block.
        """

        class Type(Enum):
            """
            Entry distinguishes arrays (lists in python) and inline
            tables, which are Mappings, but within curly braces.
            """
            LIST = 0
            MAP = 1

        def __init__(self, name, value, size: int):
            self._quote_if_str(name)
            self.name = name
            self.type = self.Type.MAP \
                if isinstance(value, Mapping) else self.Type.LIST
            self.size = size

        def __repr__(self) -> str:
            return f"<{self.__str__()}>"

        @staticmethod
        def _quote_if_str(v):
            return f"'{v}'" if v is str else v

    class __ClosingEntry(_Entry):
        def __str__(self) -> str:
            name = self._quote_if_str(self.name)
            return f"Closing({name}, {self.type}, {self.size})"

    class __OpeningEntry(_Entry):
        def __str__(self) -> str:
            name = self._quote_if_str(self.name)
            return f"Opening({name}, {self.type}, {self.size})"

    def __list(self, data) -> None:
        """
        Converts python List into TOML inline array. Tables in this list will be
        converted into inline tables.
        """
        T = TypeVar("T", Mapping, List)

        # stack is where the data will be stored during the convertion process
        # queue is where the internal data representation will be stored
        # deck will store translated TOML before it is converted to a string
        stack: List[T, int] = []
        queue = []
        dest = []

        # Pop item from the stack and iterate through it. If item[i] is is a
        # mapping or a list, push it to the stack. Otherwise push it to a queue.
        # Each table object is surrounded by _Entry "braces".
        self.__append_object("", data, stack)
        while (len(stack)):
            e = stack.pop()
            current_stack = []
            if isinstance(e, List):
                for n in e:
                    if isinstance(n, List) or isinstance(n, Mapping):
                        self.__append_object("", n, current_stack)
                    elif isinstance(n, Tuple):
                        queue.append(n)
                    else:
                        queue.append(n)
                stack += current_stack
            elif isinstance(e, Mapping):
                for k, v in e.items():
                    if isinstance(v, List) or isinstance(v, Mapping):
                        self.__append_object(k, v, current_stack)
                    else:
                        queue.append((k, v))
                stack += current_stack
            elif isinstance(e, self._Entry):
                queue.append(e)
            else:
                queue.append(e)

        if self.prefer_inline:
            self.__translate_inline(queue, dest)
        else:
            self.__translate_std(queue, dest)
        return ''.join(dest)

    def __translate_inline(self, queue: List, dest: List) -> None:
        indent_lvl = -1
        block_size = 0
        inline = 0
        for i in range(len(queue)):
            item = queue.pop(0)
            inline_small_array = inline and block_size < self.max_block_size
            brace_indent = (self.indent * indent_lvl) if not inline else ''
            value_indent = brace_indent if not inline_small_array else ' '
            if isinstance(item, self.__OpeningEntry):
                if item.type == self._Entry.Type.MAP:
                    inline += 1
                if item.size <= self.max_block_size:
                    inline += 1
                indent_lvl += 2 if indent_lvl == -1 else 1
                block_size = item.size
                self.__brace(item, dest, brace_indent, inline)
            elif isinstance(item, self.__ClosingEntry):
                if item.type == self._Entry.Type.MAP:
                    inline -= 1
                if item.size <= self.max_block_size:
                    inline -= 1
                indent_lvl -= 1
                block_size = self.max_block_size + 1
                self.__brace(item, dest, brace_indent, inline)
            else:
                dest.append(self.__value(item, value_indent, end=''))
            last_pushed = dest[-1]
            nextitem = queue[0] if len(queue) else None
            append_comma = \
                not isinstance(nextitem, self.__ClosingEntry) and \
                len(queue) and \
                last_pushed != self.ARRAY_LEFT_BRACE and \
                last_pushed != self.INLINE_TABLE_LEFT_BRACE
            append_eol = not inline and block_size > self.max_block_size
            ending = (',' if append_comma else '') + \
                (self.eol if append_eol else ' ')
            dest.append(ending)

    def __brace(self, entry: _Entry, dest: List, indent: str, inline: bool,
                end: str = eol) -> None:
        """
        Inserts braces and keys prepended.
        Also inserts indentation and eol characters.
        If the block size less than the max_block_size, does not break
        a block into multiple lines.
        """
        inline = inline and \
            self.__entry_eq(entry, dest, indent) or \
            entry.size <= self.max_block_size and \
            isinstance(entry, self.__ClosingEntry)

        indent = "" if inline else indent
        end = '' if inline else end

        if isinstance(entry, self.__OpeningEntry):
            dest.append(indent)
            if entry.type == self._Entry.Type.MAP:
                dest.append(self.INLINE_TABLE_LEFT_BRACE)
            else:
                dest.append(self.ARRAY_LEFT_BRACE)
        else:
            if entry.type == self._Entry.Type.MAP:
                dest.append(self.INLINE_TABLE_RIGHT_BRACE)
            else:
                if indent:
                    dest.append(indent[:-4])
                dest.append(self.ARRAY_RIGHT_BRACE)

    def __translate_std(self, queue: List, dest: List) -> None:
        pass

    def __append_object(self, n: str, data, stack: List) -> None:
        """
        See comment in a __list method. Wraps stack entry with _Entry
        instances, which store its name (if this entry has name), type, size
        and indicate, where it starts and ends in the queue.
        """
        size = len(data)
        stack.insert(0, self.__OpeningEntry(n, data, size))
        stack.insert(0, data)
        stack.insert(0, self.__ClosingEntry(n, data, size))

    def __entry_eq(self, entry: _Entry, dest: List, indent: str) -> bool:
        """Prepends key equal (`key =`) to an inline-table/array."""
        if isinstance(entry, self.__OpeningEntry) and entry.name:
            dest.append(f"{indent}{entry.name} = ")
            return True
        return False


z = {
    "a": "b",
    "c": {
        "d": "e",
        "one": 1,
        "two": 2,
        "three": "four",
        "pi": 3.14,
        "Is it true?": True,
        "Or false?": False
    },
    "f": {
        "g": {
            "p": {
                "q": "r",
                "my greeting": "hello world"
            },
            "i": "j",
            "k": "l"
        },
        "m": {
            "n": "o"
        },
        "s": "t"
    },
    "u": [
        {
            "f": "g"
        },
        "h"
    ],
    "v": {
        "n": "o",
        "b": [
            "c",
            {
                "d": "e",
                "l": "m",
                "u": [
                    "s",
                    "t"
                ],
                "w": {
                    "x": "y"
                }
            },
            {
                "comma": "test"
            },
            {
                "first": 1
            },
            {
                "second": 2
            },
            "i",
            "j",
            "k",
            [
                "p",
                "q",
                "r",
                # test for max_block_size
                ["hello", "my", "dear", "friend", "how", "are", "you?"]
            ],
            {
                "third": 3
            }
        ],
        "f": "g",
        "inf": float('inf'),
        "nan": float('nan'),
        "negative": -1,
        True: True,
        False: False,
        "now": datetime.now()
        # 3.14: "pi"  # TypeError: Type '<class 'float'>' is not allowed for a key: '3.14'
    },
    "one element": [
        "it is completely alone"
    ],
    "my table": {
        "position": 3
    }
}

with open("out.toml", "wt") as f:
    toml = Py2TOML()
    data = toml.convert(z)
    f.write(data)
    print(data)
