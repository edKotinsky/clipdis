from typing import Mapping, List, Tuple, TypeVar
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
                 max_block_size: int = 1, table_root: str = ""):
        """
        Py2TOML ctor.
        `table_heading_lvl` determines the nesting level, on which headers
        "[key]" will be generated. Indent size is the amount of space
        characters. Max block size determines the length of an inlined struct
        (inline-table or array), for which inlining (placing into one line) is
        allowed.
        """
        self.__indent_size = indent_size
        self.__indent = ' ' * indent_size
        self.__max_block_size = max_block_size
        self.__heading_lvl = table_heading_lvl

    def convert(self, data: Mapping, root: str = "") -> str:
        """
        Converts Python data into TOML.
        `initial` is how the root table will be named. Default: without name.
        """
        try:
            if not root:
                self.__heading_lvl += 1
            stack = [([root], data)]
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
                            stack.append((key, v))
                        else:
                            self.__push_key_value_pair(k, v, queue)
                    stack.append(name)
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
                self.__heading_lvl -= 1

    # Internal functions

    def __push_key_value_pair(self, key, value, dest: list) -> None:
        if not isinstance(value, List):
            dest.append((key, value))
        else:
            dest.append((key, self.InlineStruct(self.__inline_object(value))))

    def __standard_table(self, ll: List, stack: List, dest: List) -> None:
        """
        Create a standard table. If length of a key with parent table names
        less or equal to heading level, then create a header (see std-table in
        toml.abnf). Otherwise, create a key-value pair.
        """
        if len(ll) <= self.__heading_lvl:
            self.__header(ll, dest)
        self.__remove_first(self.__heading_lvl, ll)
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

    class InlineStruct(object):
        """
        Indicates inline struct. See __push_key_value_pair, if the value is
        returned by __inline_object, it is wrapped in InlineStruct.
        This is to avoid quoting value due to space characters in it.
        """

        def __init__(self, s: str):
            self.value = s

    def __value(self, v, indent: str = '', end: str = eol) -> str:
        """__value incapsulates both key-value pairs and array value."""
        if isinstance(v, Tuple):
            value = v[1]
            if isinstance(value, self.InlineStruct):
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

    class _ClosingEntry(_Entry):
        def __str__(self) -> str:
            name = self._quote_if_str(self.name)
            return f"Closing({name}, {self.type}, {self.size})"

    class _OpeningEntry(_Entry):
        def __str__(self) -> str:
            name = self._quote_if_str(self.name)
            return f"Opening({name}, {self.type}, {self.size})"

    def __inline_object(self, data) -> None:
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
            if isinstance(e, List):
                for n in e:
                    if isinstance(n, List) or isinstance(n, Mapping):
                        self.__append_object("", n, stack)
                    elif isinstance(n, Tuple):
                        queue.append(n)
                    else:
                        queue.append(n)
            elif isinstance(e, Mapping):
                for k, v in e.items():
                    if isinstance(v, List) or isinstance(v, Mapping):
                        self.__append_object(k, v, stack)
                    else:
                        queue.append((k, v))
            elif isinstance(e, self._Entry):
                queue.append(e)
            else:
                queue.append(e)

        self.__translate_inline(queue, dest)
        return ''.join(dest)

    def __translate_inline(self, queue: List, dest: List) -> None:
        indent_lvl = -1
        block_size = 0
        inline = 0
        for i in range(len(queue)):
            item = queue.pop(0)
            inline_small_array = inline and block_size < self.__max_block_size
            brace_indent = (self.__indent * indent_lvl) if not inline else ''
            value_indent = brace_indent if not inline_small_array else ' '
            if isinstance(item, self._OpeningEntry):
                if item.type == self._Entry.Type.MAP:
                    inline += 1
                if item.size <= self.__max_block_size:
                    inline += 1
                indent_lvl += 2 if indent_lvl == -1 else 1
                block_size = item.size
                self.__brace(item, dest, brace_indent, inline)
            elif isinstance(item, self._ClosingEntry):
                if item.type == self._Entry.Type.MAP:
                    inline -= 1
                if item.size <= self.__max_block_size:
                    inline -= 1
                indent_lvl -= 1
                block_size = self.__max_block_size + 1
                self.__brace(item, dest, brace_indent, inline)
            else:
                dest.append(self.__value(item, value_indent, end=''))
            last_pushed = dest[-1]
            nextitem = queue[0] if len(queue) else None
            append_comma = \
                not isinstance(nextitem, self._ClosingEntry) and \
                len(queue) and \
                last_pushed != self.ARRAY_LEFT_BRACE and \
                last_pushed != self.INLINE_TABLE_LEFT_BRACE
            append_eol = not inline and block_size > self.__max_block_size
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
            entry.size <= self.__max_block_size and \
            isinstance(entry, self._ClosingEntry)

        indent = "" if inline else indent
        end = '' if inline else end

        if isinstance(entry, self._OpeningEntry):
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

    def __append_object(self, n: str, data, stack: List) -> None:
        """
        See comment in a __inline_object method. Wraps stack entry with _Entry
        instances, which store its name (if this entry has name), type, size
        and indicate, where it starts and ends in the queue.
        """
        size = len(data)
        stack.append(self._ClosingEntry(n, data, size))
        stack.append(data)
        stack.append(self._OpeningEntry(n, data, size))

    def __entry_eq(self, entry: _Entry, dest: List, indent: str) -> bool:
        """Prepends key equal (`key =`) to an inline-table/array."""
        if isinstance(entry, self._OpeningEntry) and entry.name:
            dest.append(f"{indent}{entry.name} = ")
            return True
        return False
