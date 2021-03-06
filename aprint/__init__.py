#!python3
# -*- coding: ascii -*-
from __future__ import print_function

from collections import (
    defaultdict,
    OrderedDict,
    namedtuple,
)
import types
from . import formatter
from .formatcontext import (
    FormatContextBuilder,
    get_output_stream,
    NullColorScheme,
    Options
)
from io import StringIO
import inspect

def ap(*a):
    """
    A short-cut function
    
    >>> ap(42, 'spam', ['HAM', {12: set()}])
    42
    'spam'
    [
        [0] 'HAM'
        [1] {
            12: {}
        }
    ]
    >>> 'prints _ by default'
    >>> ap()
    prints _ by default
    >>> 123
    >>> ap()
    123
    """
    if a:
        for obj in a:
            pprint(obj)
    obj = inspect.getouterframes(inspect.currentframe())[1][0].f_locals['_']
    pprint(obj)


def pprint(obj, stream=None, colored=True, **kw):
    '''
    Pretty-print a Python object to a stream [default is sys.stdout].
    '''
    stream = get_output_stream(stream, colored)
    options = Options(**kw)
    AwesomePrinter(stream=stream, options=options).pprint(obj)
    print(file=stream)


def pformat(obj, **kw):
    '''
    Format a Python object into a pretty-printed representation.
    '''
    stream = StringIO()
    options = Options(color_scheme=NullColorScheme(), **kw)
    AwesomePrinter(stream=stream, options=options).pprint(obj)
    return stream.getvalue()


class AwesomePrinter:
    def __init__(self, stream, options):
        self._stream = stream
        self._options = options
    
    def pprint(self, obj):
        context = self._context()
        text = context.format(obj)
        s = text.to_str(self._options.colorizer())
        self._stream.write(s)
    
    def _context(self):
        builder = FormatContextBuilder(
            formatter.format_object,
            formatter.format_recursive_object,
        )
        types_to_format = [
            types.MethodType,
            types.FunctionType,
            type,
            str,
            list,
            defaultdict,
            OrderedDict,
            dict,
            bool,
            int,
            float,
            set,
            tuple,
        ]
        for t in types_to_format:
            builder.add_type_formatter(t, eval("formatter.format_" + t.__name__))
        return builder.build(self._options)
