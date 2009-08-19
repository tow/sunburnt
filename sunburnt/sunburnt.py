from __future__ import absolute_import

import cgi
from itertools import islice
import urllib

import httplib2

from .schema import SolrSchema, SolrError
from .search import SolrSearch

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

    def add(self, docs, chunk=100):
        # to avoid making messages too large, we break the message every
        # chunk docs.
        for doc_chunk in grouper(docs, chunk):
            update_message = self.schema.make_update(doc_chunk)
            self.conn.update(str(update_message))

    def commit(self):
        self.conn.commit()

    def optimize(self):
        self.conn.optimize()

    def search(self, **kwargs):
        params = kwargs.copy()
        for k, v in kwargs.items():
            if hasattr(v, "items"):
                del params[k]
                params.update(v)
        print self.conn.select(params)
        return self.schema.parse_results(self.conn.select(params))

    def query(self, *args, **kwargs):
        q = SolrSearch(self)
        if len(args) + len(kwargs) > 0:
            return q.query(*args, **kwargs)
        else:
            return q


def utf8_urlencode(params):
    utf8_params = {}
    for k, v in params.items():
        if isinstance(k, unicode):
            k = k.encode('utf-8')
        if isinstance(v, unicode):
            v = v.encode('utf-8')
        utf8_params[k] = v
    return urllib.urlencode(utf8_params)

def grouper(iterable, n):
    "grouper('ABCDEFG', 3) --> [['ABC'], ['DEF'], ['G']]"
    i = iter(iterable)
    g = list(islice(i, 0, n))
    while g:
        yield g
        g = list(islice(i, 0, n))
