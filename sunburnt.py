from __future__ import absolute_import

import cgi
import math
import operator
import urllib

import httplib2
import lxml.builder
import lxml.etree
import pytz
import simplejson

h = httplib2.Http(".cache")
E = lxml.builder.ElementMaker()

def force_utf8(s):
    if isinstance(s, str):
        return s
    else:
        return s.encode('utf-8')

def _serialize_date(v):
    """ Serialize a datetime object in the format required
    by Solr. See http://wiki.apache.org/solr/IndexingDates
    This will deal with both native python datetime objects
    and mx.DateTime objects."""
    # Python datetime objects may include timezone information
    if hasattr(v, 'tzinfo') and v.tzinfo:
        # but Solr requires UTC times.
        v = v.astimezone(pytz.utc)
    t = v.strftime("%Y-%m-%dT%H:%M:%S")
    # Python datetime objects store microseconds as an attribute
    if hasattr(v, "microsecond"):
        t += ".%s" % v.microsecond
    else:
        # mx.DateTime objects have a fractional part to the second
        t += str(math.modf(v.second)[0])[1:]
    t += "Z"
    return t

def _serialize(v):
    if isinstance(v, basestring):
        return v
    elif hasattr(v, 'strftime'):
        return _serialize_date(v)
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
    response_items = ("numFound", "start", "docs", "facet_counts", "highlighting")
    def __init__(self, d):
        if isinstance(d, basestring):
            d = simplejson.loads(d)
        if d["responseHeader"]["status"] != 0:
            raise ValueError("Response indicates an error")
        for attr in self.response_items:
            try:
                setattr(self, attr, d["response"][attr])
            except KeyError:
                pass

    def __str__(self):
        return "%(numFound)s results found, starting at #%(start)s" % self.__dict__


class SolrConnection(object):
    def __init__(self, url, h=h):
        self.url = url.rstrip("/") + "/"
        self.update_url = self.url + "update/"
        self.select_url = self.url + "select/"
        self.request = h.request

    def add(self, docs):
        xml = lxml.etree.tostring(_make_update_doc(docs), encoding='utf-8')
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
s.add({"nid":"sjhdfgkajshdg", "title":"title", "caption":"caption", "description":"description", "tags":["tag1", "tag2"], "last_modified":datetime.datetime.now()})
s.commit()
print s.search(q="title")
