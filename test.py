from sunburnt import SolrInterface

import datetime

s = SolrInterface("http://localhost:8983/solr",
                  "/Users/tow/dl/solr/apache-solr-1.3.0/example/solr/conf/schema.xml")
s.add({"nid":"sjhdfgkajshdg", "title":"title", "caption":"caption", "description":"description", "tags":["tag1", "tag2"], "last_modified":datetime.datetime.now()})
s.commit()
print s.search(q="title")

# Geo stuff
# understanding query params
# testsuite
