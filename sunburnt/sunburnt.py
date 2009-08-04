from __future__ import absolute_import

import cgi
import collections
import re
import urllib

import httplib2

from .schema import SolrSchema, SolrError

h = httplib2.Http(".cache")


class SolrConnection(object):
    def __init__(self, url, h=h):
        self.url = url.rstrip("/") + "/"
        self.update_url = self.url + "update/"
        self.select_url = self.url + "select/"
        self.request = h.request

    def commit(self):
        response = self.update("<commit/>")

    def optimize(self):
        response = self.update("<optimize/>")

    def update(self, update_doc):
        body = update_doc
        headers = {"Content-Type":"text/xml; charset=utf-8"}
        r, c = self.request(self.update_url, method="POST", body=body,
                            headers=headers)
        if r.status != 200:
            raise SolrError(r, c)

    def select(self, params):
        qs = utf8_urlencode(params)
        url = "%s?%s" % (self.select_url, qs)
        r, c = self.request(url)
        if r.status != 200:
            raise SolrError(r, c)
        return c


class SolrInterface(object):
    def __init__(self, url, schemadoc):
        self.conn = SolrConnection(url)
        self.schema = SolrSchema(schemadoc)

    def add(self, docs):
        update_message = self.schema.make_update(docs)
        self.conn.update(str(update_message))

    def commit(self):
        self.conn.commit()

    def search(self, **kwargs):
        params = kwargs.copy()
        for k, v in kwargs.items():
            if hasattr(v, "items"):
                del params[k]
                params.update(v)
        return self.schema.parse_results(self.conn.select(params))

    def query(self, *args, **kwargs):
        q = SolrQuery(self)
        return q.query(*args, **kwargs)


class SolrQuery(object):
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
            self.update_search(q, self.term_or_phrase(v), name, v)
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

    def highlight(self, fields=None):
        self.options["hl"] = "true"
        if fields:
            if isinstance(fields, basestring):
                fields = [fields]
            self.options["hl.fl"] = ','.join(fields)
            # what if fields has a comma in it?
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

def utf8_urlencode(params):
    utf8_params = {}
    for k, v in params.items():
        if isinstance(k, unicode):
            k = k.encode('utf-8')
        if isinstance(v, unicode):
            v = v.encode('utf-8')
        utf8_params[k] = v
    return urllib.urlencode(utf8_params)

lucene_special_chars = re.compile(r'([+\-&|!\(\){}\[\]\^\"~\*\?:\\])')
def lqs_escape(s):
    return lucene_special_chars.sub(r'\\\1', s)
