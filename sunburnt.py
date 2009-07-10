from __future__ import absolute_import

import cgi
import urllib

import httplib2
from lxml.builder import ElementMaker
from lxml import etree
import simplejson

h = httplib2.Http(".cache")
E = ElementMaker()

def force_unicode(s):
    if isinstance(s, unicode):
        return s
    else:
        return s.encode('utf-8')


class SolrException(Exception):
    pass


class SolrConnection(object):
    def __init__(self, url):
        self.url = url.rstrip("/") + "/"
        self.update_url = self.url + "update/"
        self.select_url = self.url + "select/"

    def update(self, update_doc):
        body = force_unicode(update_doc)
        headers = {"Content-Type":"text/xml; charset=utf-8"}
        r, c = h.request(self.update_url, method="POST", body=body,
                         headers=headers)
        if r.status != 200:
            raise SolrException(r, c)

    def select(self, **kwargs):
        kwargs['wt'] = 'json'
        qs = urllib.urlencode(kwargs)
        url = "%s?%s" % (self.select_url, qs)
        r, c = h.request(url)
        if r.status != 200:
            raise SolrException(r, c)
        return simplejson.loads(c)

    @staticmethod
    def _make_update_doc(docs):
        if hasattr(docs, "items"):
            docs = [docs]
        xml = E.add(*[
                E.doc(*[
                        E.field({'name':k}, v)
                        for k, v in doc.items()])
                      for doc in docs])
        return etree.tostring(xml)

    def add(self, docs):
        self.update(self._make_update_doc(docs))



solr_xml = """
<add>
<doc>
  <field name="id">SOLR1000</field>
  <field name="name">Solr, the Enterprise Search Server</field>
  <field name="manu">Apache Software Foundation</field>
  <field name="cat">software</field>  <field name="cat">search</field>
  <field name="features">Advanced Full-Text Search Capabilities using Lucene</field>
  <field name="features">Optimized for High Volume Web Traffic</field>  <field name="features">Standards Based Open Interfaces - XML and HTTP</field>
  <field name="features">Comprehensive HTML Administration Interfaces</field>
  <field name="features">Scalability - Efficient Replication to other Solr Search Servers</field>
  <field name="features">Flexible and Adaptable with XML configuration and Schema</field>
  <field name="features">Good unicode support: h&#xE9;llo (hello with an accent over the e
)</field>
  <field name="price">0</field>
  <field name="popularity">10</field>
  <field name="inStock">true</field>
  <field name="incubationdate_dt">2006-01-17T00:00:00.000Z</field>
</doc>
</add>
"""


s = SolrConnection("http://localhost:8983/solr")
s.add({"key1":"value1", "key2":"value2"})
print s.select(q="solr")
