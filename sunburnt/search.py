from __future__ import absolute_import

import collections
import re


class SolrSearch(object):
    default_term_re = re.compile(r'^\w+$')

    def __init__(self, interface):
        self.interface = interface
        self.schema = interface.schema
        self.search = {'query':
                          {'terms':collections.defaultdict(list),
                           'phrases':collections.defaultdict(list)},
                      'filter':
                          {'terms':collections.defaultdict(list),
                           'phrases':collections.defaultdict(list)}}
        self.options = {}

    def update_search(self, q, t, k, v):
        if k and k not in self.schema.fields:
            raise ValueError("%s is not a valid field name" % k)
        self.search[q][t][k].append(v)
        return self

    def query_by_term(self, field_name=None, term=""):
        return self.update_search('query', 'term', field_name, term)

    def query_by_phrase(self, field_name=None, phrase=""):
        return self.update_search('query', 'phrase', field_name, phrase)

    def filter_by_term(self, field_name=None, term=""):
        return self.update_search('filter', 'term', field_name, term)

    def filter_by_phrase(self, field_name=None, term=""):
        return self.update_search('filter', 'phrase', field_name, phrase)

    def query(self, *args, **kwargs):
        for arg in args:
            self.update_search('query', self.term_or_phrase(arg), None, arg)
        return self.update_q('query', kwargs)

    def filter(self, *args, **kwargs):
        for arg in args:
            self.update_search('filter', self.term_or_phrase(arg), None, arg)
        return self.update_q('filter', kwargs)

    def update_q(self, q, kwargs):
        for k, v in kwargs.items():
            try:
                name, rel = k.split("__")
            except ValueError:
                name, rel = k, 'eq'
            if self.schema.fields[name].type == unicode:
                search_type = self.term_or_phrase(v)
            else:
                search_type = "terms"
            self.update_search(q, search_type, name, v)
        return self

    def facet_by(self, field, limit=None, mincount=None):
        if field not in self.schema.fields:
            raise ValueError("%s is not a valid field name" % field)
        self.options.update({"facet":"true",
                             "facet.field":field})
        if limit:
            self.options["f.%s.facet.limit" % field] = limit
        if mincount:
            self.options["f.%s.facet.mincount" % field] = mincount
        return self

    def highlight(self, fields=None, snippets=None, fragsize=None):
        self.options["hl"] = "true"
        if fields:
            if isinstance(fields, basestring):
                fields = [fields]
            self.options["hl.fl"] = ','.join(fields)
            # what if fields has a comma in it?
        if snippets is not None:
            for field in fields:
                self.options["f.%s.hl.snippets" % field] = snippets
        if fragsize is not None:
            for field in fields:
                self.options["f.%s.hl.fragsize" % field] = fragsize
        return self

    def paginate(self, start=1, rows=10):
        self.options["start"] = start
        self.options["rows"] = rows
        return self

    def execute(self):
        q = serialize_search(**self.search['query'])
        if q:
            self.options["q"] = q
        qf = serialize_search(**self.search['filter'])
        if qf:
            self.options["qf"] = qf
        return self.interface.search(**self.options)

    def term_or_phrase(self, arg):
        return 'terms' if self.default_term_re.match(arg) else 'phrases'


def serialize_search(terms, phrases):
    s = []
    for name in terms:
        if name:
            s += ['%s:%s' % (name, lqs_escape(value))
                  for value in terms[name]]
        else:
            s += [lqs_escape(value) for value in terms[name]]
    for name in phrases:
        if name:
            s += ['%s:"%s"' % (name, value)
                  for value in phrases[name]]
        else:
            s += ['"%s"' % value for value in phrases[name]]
    return ' '.join(s)

lucene_special_chars = re.compile(r'([+\-&|!\(\){}\[\]\^\"~\*\?:\\])')
def lqs_escape(s):
    if isinstance(s, unicode):
        return lucene_special_chars.sub(r'\\\1', s)
    else:
        return s
