from __future__ import absolute_import

import httplib2

h = httplib2.Http(".cache")

class SolrException(Exception):
    pass

class SolrConnection(object):
    def __init__(self, url):
        self.url = url.rstrip("/") + "/"
        self.update_url = self.url + "update/"

    def add(self, doc):
        print self.update_url
        if isinstance(doc, unicode):
            body = doc
        else:
            body = doc.encode('utf-8')
        headers = {"Content-Type":"text/xml; charset=utf-8"}
        r, c = h.request(self.update_url, method="POST", body=body,
                         headers=headers)
        if r.status != 200:
            raise SolrException(r, c)

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
s.add(solr_xml)
