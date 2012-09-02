#!python3
# -*- coding: ascii -*-

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
            with context.singleline() as ctx: 
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
        text += context.space()
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
    
    def format_empty(self, aset, context):
        text = context.text()
        header = self.format_header(aset, context)
        if header:
            text += header
            text += context.space()
        text += "{}"
        return text
    
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
    
    def format_as_key(self, atuple, context):
        return format_tuple_as_key(atuple, context)
        
    def __call__(self, atuple, context):
        if not context.is_in_key_context():
            return ListFormatter.__call__(self, atuple, context)
        return self.format_as_key(atuple, context)


def format_tuple_as_key(atuple, context):
    assert context.is_in_key_context()
    assert len(atuple) >= 1
    
    if not atuple:
        return context.text("()", "tuple")
    
    text = context.text("(", "tuple")
    text += context.format(atuple[0]) + context.text(",")
    
    for index, value in enumerate(atuple[1:], start=1):
        is_last = (index == len(atuple) - 1)
        text += context.endl()
        text += context.indent()
        text += context.space()
        text += context.format(value)
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
