from __future__ import absolute_import

from .sunburnt import utf8_urlencode, grouper


url_encode_data = (
    ({"int":3, "string":"string", "unicode":u"unicode"},
     "int=3&string=string&unicode=unicode"),
    ({"int":3, "string":"string", "unicode":u"\N{UMBRELLA}nicode"},
     "int=3&string=string&unicode=%E2%98%82nicode"),
    ({"int":3, "string":"string", u"\N{UMBRELLA}nicode":u"\N{UMBRELLA}nicode"},
     "int=3&%E2%98%82nicode=%E2%98%82nicode&string=string"),
    ({"true":True, "false":False},
     "false=false&true=true"),
    ({"list":["first", "second", "third"]},
     "list=first&list=second&list=third"),
)

def check_url_encode_data(kwargs, output):
    assert utf8_urlencode(kwargs) == output

def test_url_encode_data():
    for kwargs, output in url_encode_data:
        yield check_url_encode_data, kwargs, output
