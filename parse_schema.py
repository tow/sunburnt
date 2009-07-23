import lxml.etree

solr_types = {str:['solr.StrField', 'solr.TextField'],
              bool:['solr.BoolField'],
              int:['solr.IntField', 'solr.SortableIntField'],
              long:['solr.LongField', 'solr.SortableLongField'],
              float:['solr.FloatField', 'solr.SortableFloatField',
                     'solr.DoubleField', 'solr.SortableDoubleField']}
 
schemadoc = lxml.etree.parse("/Users/tow/dl/solr/apache-solr-1.3.0/example/solr/conf/schema.xml")

field_types = {}
for t, fields in solr_types.items():
    xpath = "/schema/types/fieldType["+" or ".join("@class='%s'"% field for field in fields)+"]/@name"
    field_types[t] = schemadoc.xpath(xpath)

inverted_field_types = {}
for t, fields in field_types.items():
    for field in fields:
        inverted_field_types[field] = t

print field_types
print inverted_field_types

schema_fields = {}
for field in schemadoc.xpath("/schema/fields/field"):
    schema_fields[field.attrib['name']] = inverted_field_types.get(field.attrib['type'], 'UNKNOWN')

print schema_fields

#datefields = schemadoc.xpath("/schema/types/fieldType[@class='solr.DateField']/@name")

