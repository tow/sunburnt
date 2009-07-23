from __future__ import absolute_import

import cgi
import urllib

import httplib2
import simplejson

h = httplib2.Http(".cache")

from schema import SolrSchema, SolrResults, SolrUpdate, SolrError


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
        qs = urllib.urlencode(params)
        url = "%s?%s" % (self.select_url, qs)
        r, c = self.request(url)
        if r.status != 200:
            raise SolrException(r, c)
        return simplejson.loads(c)


class SolrInterface(object):
    def __init__(self, url, schemadoc):
        self.conn = SolrConnection(url)
        self.schema = SolrSchema(schemadoc)

    def add(self, docs):
        update_message = SolrUpdate(self.schema, docs)
        self.conn.update(str(update_message))

    def commit(self):
        self.conn.commit()

    def search(self, **kwargs):
        params = kwargs.copy()
        for k, v in kwargs.items():
            if hasattr(v, "items"):
                del params[k]
                params.update(v)
        params['wt'] = 'json'
        return SolrResults(self.schema, self.conn.select(params))


import datetime
s = SolrInterface("http://localhost:8983/solr",
                  "/Users/tow/dl/solr/apache-solr-1.3.0/example/solr/conf/schema.xml")
s.add({"nid":"sjhdfgkajshdg", "title":"title", "caption":"caption", "description":"description", "tags":["tag1", "tag2"], "last_modified":datetime.datetime.now()})
s.commit()
print s.search(q="title")
