import lxml.etree

solr_types = {str:['solr.StrField'],
              bool:['solr.BoolField'],
              int:['solr.IntField', 'solr.SortableIntField'],
              long:['solr.LongField', 'solr.SortableLongField'],
              float:['solr.FloatField', 'solr.SortableFloatField',
                     'solr.DoubleField', 'solr.SortableDoubleField']}
 
schemadoc = lxml.etree.parse("/Users/tow/dl/solr/apache-solr-1.3.0/example/solr/conf/schema.xml")

schema_fields = {}
for t, fields in solr_types.items():
    xpath = "/schema/types/fieldType["+" or ".join("@class='%s'"% field for field in fields)+"]/@name"
    schema_fields[t] = schemadoc.xpath(xpath)

print schema_fields

#datefields = schemadoc.xpath("/schema/types/fieldType[@class='solr.DateField']/@name")

