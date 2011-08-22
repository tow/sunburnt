from __future__ import absolute_import

import cgi
import cStringIO as StringIO
from itertools import islice
import logging
import socket, time, urllib, urlparse
import warnings


from .schema import SolrSchema, SolrError
from .search import LuceneQuery, SolrSearch, MltSolrSearch, params_from_dict

MAX_LENGTH_GET_URL = 2048
# Jetty default is 4096; Tomcat default is 8192; picking 2048 to be conservative.

class SolrConnection(object):
    def __init__(self, url, http_connection, retry_timeout, max_length_get_url):
        if http_connection:
            self.http_connection = http_connection
        else:
            import httplib2
            self.http_connection = httplib2.Http()
        self.url = url.rstrip("/") + "/"
        self.update_url = self.url + "update/"
        self.select_url = self.url + "select/"
        self.mlt_url = self.url + "mlt/"
        self.retry_timeout = retry_timeout
        self.max_length_get_url = max_length_get_url

    def request(self, *args, **kwargs):
        try:
            return self.http_connection.request(*args, **kwargs)
        except socket.error:
            if self.retry_timeout < 0:
                raise
            time.sleep(self.retry_timeout)
            return self.http_connection.request(*args, **kwargs)

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
        if len(url) > self.max_length_get_url:
            warnings.warn("Long query URL encountered - POSTing instead of GETting. This query will not be cached at the HTTP layer")
            method = "POST"
        else:
            method = "GET"
        r, c = self.request(url, method=method)
        if r.status != 200:
            raise SolrError(r, c)
        return c

    def mlt(self, params, body=None, charset="utf-8"):
        """Perform a MoreLikeThis query using

        If `body` is not None, use a POST query with the content
        of the body encoded using `charset`.

        Otherwise the content is passed as a URL and use a regular GET
        + parameter query (the parameter for the URL of the body is
        `stream.url`).
        """
        qs = urllib.urlencode(params)
        url = "%s?%s" % (self.mlt_url, qs)
        if body is not None:
            headers = {"Content-Type": "text/plain; charset=%s" % charset}
            if isinstance(body, unicode):
                body = body.encode(charset)
            r, c = self.request(url, method="POST", body=body,
                                headers=headers)
        else:
            # the body passed as a GET parameters
            r, c = self.request(url)
        if r.status != 200:
            raise SolrError(r, c)
        return c


class SolrInterface(object):
    readable = True
    writeable = True
    remote_schema_file = "admin/file/?file=schema.xml"
    def __init__(self, url, schemadoc=None, http_connection=None, mode='', retry_timeout=-1, max_length_get_url=MAX_LENGTH_GET_URL):
        self.conn = SolrConnection(url, http_connection, retry_timeout, max_length_get_url)
        self.schemadoc = schemadoc
        if mode == 'r':
            self.writeable = False
        elif mode == 'w':
            self.readable = False
        self.init_schema()

    def init_schema(self):
        if self.schemadoc:
            schemadoc = self.schemadoc
        else:
            r, c = self.conn.request(
                urlparse.urljoin(self.conn.url, self.remote_schema_file))
            if r.status != 200:
                raise EnvironmentError("Couldn't retrieve schema document from server - received status code %s\n%s" % (r.status, c))
            schemadoc = StringIO.StringIO(c)
        self.schema = SolrSchema(schemadoc)

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

    def delete_all(self):
        if not self.writeable:
            raise TypeError("This Solr instance is only for reading")
        # When deletion is fixed to escape query strings, this will need fixed.
        self.delete(queries=self.Q(**{"*":"*"}))

    def search(self, **kwargs):
        if not self.readable:
            raise TypeError("This Solr instance is only for writing")
        params = params_from_dict(**kwargs)
        return self.schema.parse_response(self.conn.select(params))

    def query(self, *args, **kwargs):
        if not self.readable:
            raise TypeError("This Solr instance is only for writing")
        q = SolrSearch(self)
        if len(args) + len(kwargs) > 0:
            return q.query(*args, **kwargs)
        else:
            return q

    def mlt_search(self, body=None, **kwargs):
        if not self.readable:
            raise TypeError("This Solr instance is only for writing")
        params = params_from_dict(**kwargs)
        return self.schema.parse_response(self.conn.mlt(params, body=body))

    def mlt_query(self, fields, body=None, url=None, query_fields=None,
                  **kwargs):
        """Perform a similarity query on MoreLikeThisHandler

        The MoreLikeThisHandler is expected to be registered at the '/mlt'
        endpoint in the solrconfig.xml file of the server.

        fields is the list of field names to compute similarity upon.
        query_fields can be used to adjust boosting values on a subset of those
        fields.

        Other MoreLikeThis specific parameters can be passed as kwargs without
        the 'mlt.' prefix.
        """
        if not self.readable:
            raise TypeError("This Solr instance is only for writing")
        q = MltSolrSearch(self, body_content=body, body_url=url)
        return q.mlt(fields, query_fields=query_fields, **kwargs)

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
