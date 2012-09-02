aprint (Yet another Pretty Printer inspired by awesome_print in Ruby)
*******************************************************************************

aprint is a Python library that pretty prints Python objects
in full color exposing their internal structure with proper indentation.
It supports not only built-in types,
but supports OrderedDict, defaultdict, and other type in standard library.

Installation
============
Install by pip
::
    $ pip install aprint

Cloning the repository
::
    $ git clone git://github.com/doloopwhile/aprint.git
    $ cd aprint
    $ python setup.py develop

Example
========
::
    >>> from aprint import pprint
    >>> data = [{"a": 1, "beta": 2.0, (1, 2):{'A','B','A','C'}}, lambda x:0, int]
    >>> pprint(data)
    [
        [0] {
            'a'   : 1
            (1,
             2): {
                'A'
                'B'
                'C'
            }
            'beta': 2.0
        }
        [1] <lambda>()
        [2] int
    ]

URL
===
PyPI: http://pypi.python.org/pypi/aprint/0.1
Github: https://github.com/doloopwhile/aprint

License
=======
Copyright (c) 2012 OMOTO Kenji
Released under the MIT license. See LICENSE file for details.


