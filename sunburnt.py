from __future__ import absolute_import

import cgi
import operator
import urllib

import httplib2
from lxml.builder import ElementMaker
from lxml import etree
import simplejson

h = httplib2.Http(".cache")
E = ElementMaker()

def force_utf8(s):
    if isinstance(s, str):
        return s
    else:
        return s.encode('utf-8')

def _serialize(v):
    if isinstance(v, basestring):
        return v
    elif hasattr(v, 'strftime'):
        return v.strftime("%Y-%m-%dT%H:%M:%S.%%sZ") % v.microsecond
    else:
        return simplejson.dumps(v)


ADD = E.add
DOC = E.doc
FIELD = E.field

def _serialize_field(name, value):
    if not hasattr(value, "__iter__"):
        value = [value]
    return [FIELD({'name':name}, _serialize(v)) for v in value]

def _serialize_fields(doc):
    if not doc:
       return DOC()
    return DOC(*reduce(operator.add,
                       [_serialize_field(k, v) for k, v in doc.items()]))

def _make_update_doc(docs):
    if hasattr(docs, "items"):
        docs = [docs]
    return ADD(*[_serialize_fields(doc) for doc in docs])


class SolrException(Exception):
    pass


class SolrResults(object):
    def __init__(self, d):
        if isinstance(basestring, d):
            d = simplejson.loads(d)


class SolrConnection(object):
    def __init__(self, url, h=h):
        self.url = url.rstrip("/") + "/"
        self.update_url = self.url + "update/"
        self.select_url = self.url + "select/"
        self.request = h.request

    def add(self, docs):
        xml = etree.tostring(_make_update_doc(docs), encoding='utf-8')
        self.update(xml)

    def search(self, **kwargs):
        params = kwargs.copy()
        for k, v in kwargs.items():
            if hasattr(v, "items"):
                del params[k]
                params.update(v)
        params['wt'] = 'json'
        return SolrResults(self.select(params))

    def commit(self):
        response = self.update("<commit/>")

    def optimize(self):
        response = self.update("<optimize/>")

    def update(self, update_doc):
        body = force_utf8(update_doc)
        headers = {"Content-Type":"text/xml; charset=utf-8"}
        r, c = self.request(self.update_url, method="POST", body=body,
                            headers=headers)
        if r.status != 200:
            raise SolrException(r, c)

    def select(self, params):
        qs = urllib.urlencode(params)
        url = "%s?%s" % (self.select_url, qs)
        r, c = self.request(url)
        if r.status != 200:
            raise SolrException(r, c)
        return simplejson.loads(c)


import datetime
s = SolrConnection("http://localhost:8983/solr")
s.add({"key1":"value1", "key2":"value2", "key3":["value_A", "value_B"], "int":1, "date":datetime.datetime.now()})
s.commit()
print s.select(q="solr")
