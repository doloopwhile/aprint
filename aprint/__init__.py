#!python3
# -*- coding: ascii -*-
import sys
from abc import (
    abstractmethod,
    ABCMeta
)
from collections import (
    defaultdict,
    OrderedDict,
    namedtuple,
    Mapping,
)
from copy import copy
from contextlib import contextmanager
import operator
import types
import inspect

import colorama

def get_output_stream(stream, colored):
    if stream is not None:
        return stream
    if not colored or sys.platform != 'win32':
        return sys.stdout
    
    from colorama.ansitowin32 import AnsiToWin32
    return AnsiToWin32(sys.stdout, True, True, True)

def pprint(obj, stream=None, colored=True, **kw):
    stream = get_output_stream(stream, colored)
    color_scheme = ColorScheme()
    return AwesomePrinter(
        stream=stream,
        color_scheme=color_scheme,
        **kw).pprint(obj)

def pformat(obj, colored=False, **kw):
    stream = StringIO()
    AwesomePrinter(stream=stream, color_scheme=None, **kw).pprint(obj)
    return stream.getvalue()



class NullColorizer:
    def __call__(self, astr, color_key):
        return astr
    

class AwesomePrinter:
    def __init__(self, stream, color_scheme=None, **kw):
        self._stream = stream
        self._color_scheme = color_scheme
        self._options = Options(**kw)
    
    def pprint(self, obj):
        context = self._context()
        text = context.format(obj)
        s = text.to_string(self._colorizer())
        print(s, file=self._stream)
    
    def _colorizer(self):
        if not self._color_scheme:
            return NullColorizer()
        return self._color_scheme.colorizer()
    
    def _context(self):
        builder = FormatContextBuilder()
        builder.add_type_formatter(types.FunctionType, format_function)
        builder.add_type_formatter(types.MethodType, format_method)
        for t in [type, str, list, defaultdict, OrderedDict, dict, bool, int, float, set, tuple]:
            builder.add_type_formatter(t, eval("format_" + t.__name__))
        return builder.build(self._options)


Coloring = namedtuple("Coloring", "fg bg")

class BaseColorScheme(defaultdict):
    BLACK   = "black"
    BLUE    = "blue"
    CYAN    = "cyan"
    GREEN   = "green"
    MAGENTA = "magenta"
    RED     = "red"
    WHITE   = "white"
    YELLOW  = "yellow"
    
    BRIGHT = "bright"
    DIM    = "dim"
    NORMAL = "normal"
    
    def __init__(self):
        defaultdict.__init__(self, lambda: None)
    
    def colorizer(self):
        return self.colorize
    
    def colorize(self, astr, color_key):
        if color_key is None:
            return astr
        
        fg = self[color_key, "fg"]
        bg = self[color_key, "bg"]
        style = self[color_key, "style"]
        
        if style is not None:
            astr = getattr(colorama.Style, style.upper()) + astr
        if fg is not None:
            astr = getattr(colorama.Fore, fg.upper()) + astr
        if bg is not None:
            astr = getattr(colorama.Back, bg.upper()) + astr
        astr += colorama.Back.RESET + colorama.Fore.RESET + colorama.Style.RESET_ALL
        return astr
    


class ColorScheme(BaseColorScheme):
    def __init__(self):
        BaseColorScheme.__init__(self)
        self["str", "fg"] = self.YELLOW
        self["str", "style"] = self.BRIGHT
        
        self["list", "fg"] = self.GREEN
        self["list", "style"] = self.BRIGHT
        
        self["dict", "fg"] = self.RED
        self["dict", "style"] = self.BRIGHT
        
        self["set", "fg"] = self.CYAN
        self["set", "style"] = self.BRIGHT
        
        self["int", "fg"] = self.CYAN
        self["int", "style"] = self.BRIGHT

        self["float", "fg"] = self.CYAN
        self["float", "style"] = self.BRIGHT
        
        self["True", "fg"] = self.GREEN
        self["True", "style"] = self.BRIGHT
        
        self["False", "fg"] = self.RED
        self["False", "style"] = self.BRIGHT
        
        self["type", 'fg'] = self.WHITE
        self["type", 'style'] = self.BRIGHT
        
        self["function", 'fg'] = self.MAGENTA
        self["function", 'style'] = self.BRIGHT
        


class Options(dict):
    def __init__(self, indent=4, limit=7, doctype="text", plain=True, colors={}, multiline=True):
        dict.__init__(self)
        self["indent"] = indent
        self["limit"] = limit
        self["doctype"] = doctype
        self["plain"] = plain
        self["colors"] = ColorScheme()
        self["colors"].update(colors)
        self["multiline"] = multiline
        self["limit_key_length"] = 16
        self


class Colorizer:
    def __init__(self, colors):
        self._colors = colors
    
    def __call__(self, astr, color_key):
        color = self._colors[color_key]
        return color


class Text:
    def rjust(self, length):
        return self + " " * (length - len(self))
    
    def __radd__(self, astr):
        assert isinstance(astr, str)
        return SingleText(astr) + self

    def __nonzero__(self):
        return len(self) != 0


class ComplexText(Text):
    def __init__(self):
        Text.__init__(self)
        self._subtexts = []
    
    def __iadd__(self, t):
        if isinstance(t, str):
            self._subtexts.append(SingleText(t))
        elif isinstance(t, SingleText):
            self._subtexts.append(t)
        else:
            assert isinstance(t, ComplexText)
            self._subtexts.extend(t._subtexts)
        return self
    
    def __add__(self, t):
        text = copy(self)
        text += t
        return text
    
    def to_string(self, colorizer=None):
        return "".join(text.to_string(colorizer) for text in self._subtexts)
    
    def __len__(self):
        return sum(map(len, self._subtexts))


class SingleText:
    def __init__(self, string, color=None):
        Text.__init__(self)
        self._string = string
        self._color = color
    
    def __add__(self, t):
        if isinstance(t, str):
            t = SingleText(t)
        ret = ComplexText()
        ret += self
        ret += t
        return ret
    
    def to_string(self, colorizer=None):
        if colorizer is None:
            return self._string
        else:
            return colorizer(self._string, self._color)
    
    def __len__(self):
        return len(self._string)


class BaseFormatContext(metaclass=ABCMeta):
    def __init__(self, options):
        self._indentation = 0
        self._options = options
        self._callstack = []
        self._key_context = False
    
    def format(self, obj):
        recursive = (id(obj) in self._callstack)
        self._callstack.append(id(obj))
        try:
            return self.get_formatter(obj, recursive)(obj, self)
        finally:
            self._callstack.pop(-1)
    
    def text(self, string=None, color=None):
        text = ComplexText()
        if string is not None:
            text += SingleText(string, color)
        return text
    
    def endl(self):
        return SingleText("\n")

    def space(self):
        return SingleText(' ')
    
    def one_indent(self):
        return " " * self._options["indent"]
        
    def indent(self):
        return " " * self._indentation
    
    def outdent(self):
        return ' ' * self._indentation
    
    def limit_str_length(self):
        return 32
    
    def limit(self):
        return self._options["limit"]
    
    def limit_key_length(self):
        return self._options["limit_key_length"]
    
    def show_list_index(self):
        return True
    
    def sort_keys(self):
        return True
        
    @abstractmethod
    def get_formatter(self, obj):
        pass
    
    @contextmanager
    def indented(self):
        c = copy(self)
        c._indentation += self._options["indent"]
        yield c
    
    @contextmanager
    def unindented(self):
        c = copy(self)
        c._indentation -= self._options["indent"]
        yield c
    
    @contextmanager
    def key_context(self):
        c = copy(self)
        c._key_context = True
        yield c
    
    def is_in_key_context(self):
        return self._key_context


class IsInstance:
    """
    a wrapper for built-in isinstance function.
    IsInstance(type)(object) == isinstance(object, type)
    """
    def __init__(self, atype):
        assert isinstance(atype, type)
        self._type = atype
    
    def match(self, object):
        return isinstance(object, self._type)


FormatterRegistration = namedtuple("FormatterRegistration", "formatter rule recursive priority")

class FormatContext(BaseFormatContext):
    def __init__(self, formatters, format_object, format_recursive_object, options):
        BaseFormatContext.__init__(self, options)
        self._formatters = formatters
        self._format_object = format_object
        self._format_recursive_object = format_recursive_object 
    
    def get_formatter(self, obj, recursive=False):
        matched_formatters = [
            reg for reg in self._formatters
                if reg.rule.match(obj) and bool(reg.recursive) == bool(recursive)]
        
        if not matched_formatters:
            if recursive:
                return self._format_recursive_object
            else:
                return self._format_object
        
        matched_formatters.sort(key=operator.attrgetter("priority"), reverse=True)
        return matched_formatters[0].formatter


class FormatContextBuilder:
    _ContextClass = FormatContext
    def __init__(self):
        self._formatters = []
    
    def build(self, options):
        return self._ContextClass(
            list(self._formatters),
            format_object,
            format_recursive_object,
            options
        )
    
    def add_type_formatter(self, type, formatter, recursive=False, priority=0):
        self._formatters.append(
            FormatterRegistration(
                formatter=formatter,
                rule=IsInstance(type),
                recursive=recursive,
                priority=priority
            )
        )


def format_object(obj, context):
    return context.text(str(obj))


def format_recursive_object(obj, context):
    return context.text(
        "<Recursion on {type.__name__} with id={id}>".format(
            type=type(obj), id=id(obj)))


def format_int(obj, context):
    return context.text(str(obj), color="int")

def format_float(obj, context):
    return context.text(str(obj), color="float")

def format_bool(obj, context):
    if obj:
        return context.text(str(obj), color="True")
    else:
        return context.text(str(obj), color="False")



class StrFormatter:
    mid = "..."
    def get_limited(self, astr, context):
        if context.limit_str_length() and len(astr) > context.limit_str_length() - len(self.mid):
            head_len = (context.limit_str_length() - len(self.mid)) // 2
            head = astr[:head_len]
            tail_len = context.limit_str_length() - len(self.mid) - len(head)
            tail = astr[-tail_len-1:]
            return head + self.mid + tail
        else:
            return astr
    
    def format_content(self, astr, context):
        return str(self.get_limited(astr, context))
    
    def header(self, astr, context):
        if type(astr) == str:
            return ""
        else:
            return type(astr).__name__ + " "
    
    def __call__(self, astr, context):
        s = "{header}'{content}'".format(
                header=self.header(astr, context),
                length=len(astr),
                content=self.format_content(astr, context))
        return context.text(s, "str")


def format_str(obj, context):
    return StrFormatter()(obj, context)


class ListFormatter:
    def format_index(self, alist, context, index):
        index_width = len(str(len(alist) - 1))
        text = context.text()
        text += context.indent()
        if context.show_list_index():
            text += context.text("[")
            text += context.format(index).rjust(index_width)
            text += context.text("] ")
        return text
    
    def format_abbr(self, alist, context, start, end):
        text = context.text()
        with context.indented() as ctx:
            text += ctx.indent()
            if ctx.show_list_index():
                text += ctx.text("[")
                text += ctx.format(start)
                text += ctx.text("] ... [")
                text += ctx.format(end - 1)
                text += ctx.text("]")
            else:
                text += ctx.text(" ... ", "list")
            text += ctx.endl()
        return text
        
    def abbr_range(self, length, context):
        if context.limit() is None or length <= context.limit():
            return None
        else:
            from math import (
                ceil,
                floor
            )
            abbr_start = int(ceil(context.limit() / 2))
            abbr_end   = int(len(alist) - floor(context.limit() / 2))
            return (abbr_start, abbr_end)
    
    def format_item(self, alist, context, index, is_last):
        with context.indented() as ctx:
            text = ctx.text()
            text += self.format_index(alist, ctx, index)
            text += ctx.format(alist[index])
            if not is_last:
                text += ctx.endl()
            return text
    
    def format_items(self, alist, context):
        abbr = self.abbr_range(len(alist), context)
        text = context.text()
        if abbr is None:
            for index, item in enumerate(alist):
                is_last = (index == len(alist) - 1)
                text += self.format_item(alist, context, index, is_last)
        else:
            abbr_start, abbr_end = abbr
            for index, item in islice(enumerate(alist), abbr_start):
                text += self.format_item(alist, context, index)
            text += self.format_abbr(alist, context, abbr_start, abbr_end)
            for index, item in islice(enumerate(alist), abbr_end, len(alist)):
                is_last = (index == len(alist) - 1)
                text += self.format_item(alist, context, index, is_last)
        return text
    
    def format_empty(self, alist, context):
        return context.text("[]", "list")
    
    def format_left_paren(self, alist, context):
        return context.text("[", "list")
    
    def format_right_paren(self, alist, context):
        return context.text("]", "list")
    
    def __call__(self, obj, context):
        alist = obj
        if not alist:
            return self.format_empty(alist, context)
        text = context.text()
        
        text += self.format_left_paren(alist, context)
        text += context.endl()
        text += self.format_items(alist, context)
        text += context.endl()
        text += context.outdent()
        text += self.format_right_paren(alist, context)
        return text

format_list = ListFormatter()



class DictFormatter:
    def format_empty(self, adict, context):
        return context.text("{}", "dict")
    
    def format_item(self, adict, context, key, key_width, index):
        value = adict[key]
        with context.indented() as ctx:
            text = ctx.text()
            text += ctx.indent()
            with ctx.key_context() as ctx_key:
                formated_key = ctx_key.format(key)
            
            if len(formated_key) < ctx.limit_key_length():
                text += formated_key.rjust(key_width)
            else:
                text += formated_key

            text += ": "
            text += ctx.format(value)
            text += ctx.endl()
            return text
    
    def key_width(self, adict, context):
        key_strs = []
        for key in adict:
            options = copy(context._options)
            options["plain"] = True
            options["multiline"] = False
            ctx = copy(context)
            ctx._options = options
            key_strs.append(ctx.format(key))
        return max(len(key_str) for key_str in key_strs if len(key_str) < context.limit_key_length())
    
    def format_items(self, adict, context):
        keys = list(adict.keys())
        try:
            keys.sort()
        except TypeError:
            pass
        
        data = []
        key_width = self.key_width(adict, context)
        text = context.text()
        for i, key in enumerate(keys):
            text += self.format_item(adict, context, key, key_width, i)
        return text
    
    def format_header(self, adict, context):
        if type(adict) == dict:
            return context.text()

        return context.text(type(adict).__name__, 'type')

    
    def __call__(self, adict, context):
        if not adict:
            return self.format_empty(adict, context)
        
        text = context.text()
        header = self.format_header(adict, context)
        if header:
            text += header
            text += context.space()

        text += context.text("{", "dict")
        text += context.endl()
        text += self.format_items(adict, context)
        text += context.outdent() + context.text("}", "dict")
        return text


def format_dict(obj, context):
    return DictFormatter()(obj, context)


class DefaultdictFormatter(DictFormatter):
    def format_header(self, adict, context):
        type_name = type(adict).__name__
        text = context.text()
        text += context.text(type_name, 'type')
        text += ' '
        text += context.format(adict.default_factory)
        return text


def format_defaultdict(obj, context):
    return DefaultdictFormatter()(obj, context)


class OrderedDictFormatter(DictFormatter):
    def format_item(self, adict, context, key, key_width, index):
        value = adict[key]
        with context.indented() as ctx:
            text = ctx.text()
            text += ctx.indent()
            text += '[' + ctx.format(index) + ']'
            text += ctx.space()
            with ctx.key_context() as ctx_key:
                formated_key = ctx_key.format(key)
            
            if len(formated_key) < ctx.limit_key_length():
                text += formated_key.rjust(key_width)
            else:
                text += formated_key

            text += ": "
            text += ctx.format(value)
            text += ctx.endl()
            return text

def format_OrderedDict(obj, context):
    return OrderedDictFormatter()(obj, context)

class SetFormatter:
    def format_items(self, aset, context):
        items = list(aset)
        try:
            items.sort()
        except TypeError:
            pass
        
        text = context.text()
        for i, item in enumerate(items):
            text += self.format_item(aset, context, item, i)
        return text
        
    def format_item(self, aset, context, item, index):
        with context.indented() as ctx:
            text = ctx.text()
            text += ctx.indent()
            text += ctx.format(item)
            text += ctx.endl()
            return text
    
    def format_header(self, aset, context):
        if type(aset) == set:
            return context.text()
        return context.text(type(aset).__name__, 'type')
    
    def __call__(self, aset, context):
        if not aset:
            return self.format_empty(aset, context)
        text = context.text()
        header = self.format_header(aset, context)
        if header:
            text += header
            text += context.space()
        text += context.text("{", "set")
        text += context.endl()
        text += self.format_items(aset, context)
        text += context.outdent() + context.text("}", "set")
        return text


def format_set(obj, context):
    return SetFormatter()(obj, context)


class TupleFormatter(ListFormatter):
    def format_left_paren(self, atuple, context):
        return context.text("(", "tuple")
    
    def format_right_paren(self, atuple, context):
        return context.text(")", "tuple")
    
    def __call__(self, atuple, context):
        if not context.is_in_key_context():
            return ListFormatter.__call__(self, atuple, context)
        return format_tuple_key(atuple, context)


def format_tuple_key(atuple, context):
    assert context.is_in_key_context()
    assert len(atuple) >= 1
    
    if not atuple:
        return context.text("()", "tuple")
    
    text = context.text("(", "tuple")
    text += context.format(atuple[0]) + context.text(",")
    
    for index, value in enumerate(atuple[1:], start=1):
        is_last = (index == len(atuple) - 1)
        text += context.endl() + context.indent() + " " + context.format(value)
        if not is_last:
            text += context.text(",")
    
    text += context.text(")", "tuple")
    return text

def format_tuple(obj, context):
    return TupleFormatter()(obj, context)


class TypeFormatter:
    def __call__(self, atype, context):
        return context.text(atype.__name__, 'type')

def format_type(obj, context):
    return TypeFormatter()(obj, context)


class FunctionFormatter:
    def format_args(self, afunction, context):
        return context.text('()')

    def __call__(self, afunction, context):
        text = context.text(afunction.__name__, 'function')
        text += self.format_args(afunction, context)

        return text


def format_function(obj, context):
    return FunctionFormatter()(obj, context)


class MethodFormatter(FunctionFormatter):
    def __call__(self, amethod, context):
        text = context.format(amethod.__self__)
        text += '.'
        text += super().__call__(amethod, context)
        return text


def format_method(obj, context):
    return MethodFormatter()(obj, context)
