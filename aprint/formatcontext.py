#!python3
# -*- coding: ascii -*-
import sys

from copy import copy
from contextlib import contextmanager
import operator
from collections import (
    defaultdict,
    namedtuple,
)

from abc import (
    ABCMeta,
    abstractmethod
)

import colorama
if sys.platform == 'win32':
    import colorama.ansitowin32


def get_output_stream(stream, colored):
    if stream is not None:
        return stream
    
    if not colored or sys.platform != 'win32':
        return sys.stdout
    
    return colorama.ansitowin32.AnsiToWin32(sys.stdout, True, True, True)


class ColorScheme(defaultdict):
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

for name in 'BLACK BLUE CYAN GREEN MAGENTA RED WHITE YELLOW BRIGHT DIM NORMAL'.split():
    setattr(ColorScheme, name.upper(), name.upper()) 


class DefaultColorScheme(ColorScheme):
    def __init__(self):
        ColorScheme.__init__(self)
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


class NullColorScheme:
    def colorizer(self):
        return self.colorize
    
    def colorize(self, astr, color_key):
        return astr


class Options(dict):
    def __init__(self, indent=4, limit=7, doctype="text", plain=True, color_scheme=None, multiline=True):
        dict.__init__(self)
        self["indent"] = indent
        self["limit"] = limit
        self["doctype"] = doctype
        self["plain"] = plain
        self["color_scheme"] = color_scheme or DefaultColorScheme()
        self["multiline"] = multiline
        self["limit_key_length"] = 16
    
    def colorizer(self):
        return self["color_scheme"].colorizer()


class Text:
    '''
    String with style info. Used to abstract colorama
    '''
    __meta__ = ABCMeta
    
    @abstractmethod
    def to_str(self):
        '''
        Translate to built-in str object
        '''
        pass
    
    @abstractmethod
    def __add__(self):pass

    @abstractmethod
    def __len__(self):pass
    
    def rjust(self, length):
        '''Similar to str.rjust '''
        return self + " " * (length - len(self))
    
    def __radd__(self, astr):
        assert isinstance(astr, str)
        return SingleText(astr) + self
    
    def __nonzero__(self):
        return len(self) != 0


class SingleText(Text):
    '''
    String with style info. Used to abstract colorama.
    Represents string colored with one color.
    '''
    def __init__(self, string='', color=None):
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
    
    def to_str(self, colorizer=None):
        if colorizer is None:
            return self._string
        else:
            return colorizer(self._string, self._color)
    
    def __len__(self):
        return len(self._string)


class ComplexText(Text):
    '''
    String with style info. Used to abstract colorama.
    Represents string colored with multiple colors or
    concatenated SingleText instances.
    This type is basically immutable, but mutable by __iadd__.
    '''
    def __init__(self, string='', color=None):
        Text.__init__(self)
        self._subtexts = []
        if string != '':
            self += SingleText(string, color)
    
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
    
    def to_str(self, colorizer=None):
        return "".join(text.to_str(colorizer) for text in self._subtexts)
    
    def __len__(self):
        return sum(map(len, self._subtexts))


class FormatContext(metaclass=ABCMeta):
    @abstractmethod
    def get_formatter(self, obj):
        pass
    
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
    
    @contextmanager
    def singleline(self):
        c = copy(self)
        c._options["multiline"] = False
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
    
    def __call__(self, object):
        return isinstance(object, self._type)


class FormatContextWithFormatters(FormatContext):
    def __init__(self, formatters, format_object, format_recursive_object, options):
        FormatContext.__init__(self, options)
        self._formatters = formatters
        self._format_object = format_object
        self._format_recursive_object = format_recursive_object 
    
    def get_formatter(self, obj, recursive=False):
        matched_formatters = [
            reg for reg in self._formatters
                if reg.match(obj) and bool(reg.recursive) == bool(recursive)]
        
        if not matched_formatters:
            if recursive:
                return self._format_recursive_object
            else:
                return self._format_object
        
        matched_formatters.sort(key=operator.attrgetter("priority"), reverse=True)
        return matched_formatters[0].formatter


FormatterRegistration = namedtuple("FormatterRegistration", "formatter match recursive priority")

class FormatContextBuilder:
    def __init__(self, format_object, format_recursive_object):
        self._formatters = []
        self._format_object = format_object
        self._format_recursive_object = format_recursive_object
    
    def create_format_context(self, *a, **kw):
        return FormatContextWithFormatters(*a, **kw)
    
    def build(self, options):
        return self.create_format_context(
            list(self._formatters),
            self._format_object,
            self._format_recursive_object,
            options
        )
    
    def add_type_formatter(self, type, formatter, recursive=False, priority=0):
        self._formatters.append(
            FormatterRegistration(
                formatter=formatter,
                match=IsInstance(type),
                recursive=recursive,
                priority=priority
            )
        )

