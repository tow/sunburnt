from __future__ import absolute_import

import cgi
import cStringIO as StringIO
from itertools import islice
import logging
import urllib, urlparse
import warnings

import httplib2

from .schema import SolrSchema, SolrError
from .search import LuceneQuery, SolrSearch, params_from_dict


class SolrConnection(object):
    def __init__(self, url, http_connection=None):
        if not http_connection:
            http_connection = httplib2.Http()
        self.url = url.rstrip("/") + "/"
        self.update_url = self.url + "update/"
        self.select_url = self.url + "select/"
        self.request = http_connection.request

    def commit(self, wait_flush=True, wait_searcher=True):
        response = self.commit_or_optimize("commit",
                                           wait_flush, wait_searcher)

    def optimize(self, wait_flush=True, wait_searcher=True):
        response = self.commit_or_optimize("optimize",
                                           wait_flush, wait_searcher)

    def commit_or_optimize(self, verb, wait_flush, wait_searcher):
        wait_flush = "true" if wait_flush else "false"
        wait_searcher = "true" if wait_searcher else "false"
        response = self.update('<%s waitFlush="%s" waitSearcher="%s"/>' %
                               (verb, wait_flush, wait_searcher))

    def rollback(self):
        response = self.update("<rollback/>")

    def update(self, update_doc):
        body = update_doc
        headers = {"Content-Type":"text/xml; charset=utf-8"}
        r, c = self.request(self.update_url, method="POST", body=body,
                            headers=headers)
        if r.status != 200:
            raise SolrError(r, c)

    def select(self, params):
        qs = urllib.urlencode(params)
        url = "%s?%s" % (self.select_url, qs)
        r, c = self.request(url)
        if r.status != 200:
            raise SolrError(r, c)
        return c


class SolrInterface(object):
    readable = True
    writeable = True
    remote_schema_file = "admin/file/?file=schema.xml"
    def __init__(self, url, schemadoc=None, http_connection=None, mode=''):
        if not http_connection:
            http_connection = httplib2.Http()
        self.conn = SolrConnection(url, http_connection)
        if not schemadoc:
            r, c = http_connection.request(
                urlparse.urljoin(url, self.remote_schema_file))
            if r.status != 200:
                raise EnvironmentError("Couldn't retrieve schema document from server - received status code %s\n%s" % (r.status, c))
            schemadoc = StringIO.StringIO(c)
        self.schema = SolrSchema(schemadoc)
        if mode == 'r':
            self.writeable = False
        elif mode == 'w':
            self.readable = False

    def add(self, docs, chunk=100):
        if not self.writeable:
            raise TypeError("This Solr instance is only for reading")
        if hasattr(docs, "items") or not hasattr(docs, "__iter__"):
            docs = [docs]
        # to avoid making messages too large, we break the message every
        # chunk docs.
        for doc_chunk in grouper(docs, chunk):
            update_message = self.schema.make_update(doc_chunk)
            self.conn.update(str(update_message))

    def delete(self, docs=None, queries=None):
        if not self.writeable:
            raise TypeError("This Solr instance is only for reading")
        if not docs and not queries:
            raise SolrError("No docs or query specified for deletion")
        elif docs is not None and (hasattr(docs, "items") or not hasattr(docs, "__iter__")):
            docs = [docs]
        delete_message = self.schema.make_delete(docs, queries)
        self.conn.update(str(delete_message))

    def commit(self, *args, **kwargs):
        if not self.writeable:
            raise TypeError("This Solr instance is only for reading")
        self.conn.commit(*args, **kwargs)

    def optimize(self, *args, **kwargs):
        if not self.writeable:
            raise TypeError("This Solr instance is only for reading")
        self.conn.optimize(*args, **kwargs)

    def rollback(self):
        if not self.writeable:
            raise TypeError("This Solr instance is only for reading")
        self.conn.rollback()

    def clear_all(self):
        if not self.writeable:
            raise TypeError("This Solr instance is only for reading")
        # When deletion is fixed to escape query strings, this will need fixed.
        self.delete(queries="*:*")

    def search(self, **kwargs):
        if not self.readable:
            raise TypeError("This Solr instance is only for writing")
        params = params_from_dict(**kwargs)
        return self.schema.parse_results(self.conn.select(params))

    def query(self, *args, **kwargs):
        if not self.readable:
            raise TypeError("This Solr instance is only for writing")
        q = SolrSearch(self)
        if len(args) + len(kwargs) > 0:
            return q.query(*args, **kwargs)
        else:
            return q

    def Q(self, *args, **kwargs):
        q = LuceneQuery(self.schema)
        q.add(args, kwargs)
        return q


def grouper(iterable, n):
    "grouper('ABCDEFG', 3) --> [['ABC'], ['DEF'], ['G']]"
    i = iter(iterable)
    g = list(islice(i, 0, n))
    while g:
        yield g
        g = list(islice(i, 0, n))
