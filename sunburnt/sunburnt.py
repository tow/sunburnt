from __future__ import absolute_import

from os import path
from lxml import etree
import cStringIO as StringIO
from itertools import islice
import socket, time, urllib, urlparse, shutil, tempfile
import warnings


from .schema import SolrSchema, SolrError
from .search import LuceneQuery, MltSolrSearch, SolrSearch, params_from_dict

MAX_LENGTH_GET_URL = 2048
# Jetty default is 4096; Tomcat default is 8192; picking 2048 to be conservative.

class SolrConnection(object):
    readable = True
    writeable = True
    def __init__(self, url, http_connection, mode, retry_timeout, max_length_get_url, format):
        if http_connection:
            self.http_connection = http_connection
        else:
            import httplib2
            self.http_connection = httplib2.Http()
        if mode == 'r':
            self.writeable = False
        elif mode == 'w':
            self.readable = False
        self.url = url.rstrip("/") + "/"
        self.update_url = self.url + "update/"
        self.select_url = self.url + "select/"
        self.mlt_url = self.url + "mlt/"
        self.retry_timeout = retry_timeout
        self.max_length_get_url = max_length_get_url
        self.format = format

    def request(self, *args, **kwargs):
        try:
            return self.http_connection.request(*args, **kwargs)
        except socket.error:
            if self.retry_timeout < 0:
                raise
            time.sleep(self.retry_timeout)
            return self.http_connection.request(*args, **kwargs)

    def commit(self, waitSearcher=None, expungeDeletes=None, softCommit=None):
        self.update('<commit/>', commit=True,
                waitSearcher=waitSearcher, expungeDeletes=expungeDeletes, softCommit=softCommit)

    def optimize(self, waitSearcher=None, maxSegments=None):
        self.update('<optimize/>', optimize=True,
            waitSearcher=waitSearcher, maxSegments=maxSegments)

    # For both commit & optimize above, we use the XML body instead
    # of the URL parameter, because if we're using POST (which we
    # should) then only the former works.

    def rollback(self):
        self.update("<rollback/>")

    def update(self, update_doc, **kwargs):
        if not self.writeable:
            raise TypeError("This Solr instance is only for reading")
        body = update_doc
        if body:
            headers = {"Content-Type":"text/xml; charset=utf-8"}
        else:
            headers = {}
        url = self.url_for_update(**kwargs)
        r, c = self.request(url, method="POST", body=body,
                            headers=headers)
        if r.status != 200:
            raise SolrError(r, c)

    def url_for_update(self, commit=None, commitWithin=None, softCommit=None, optimize=None, waitSearcher=None, expungeDeletes=None, maxSegments=None):
        extra_params = {}
        if commit is not None:
            extra_params['commit'] = "true" if commit else "false"
        if commitWithin is not None:
            try:
                extra_params['commitWithin'] = str(int(commitWithin))
            except (TypeError, ValueError):
                raise ValueError("commitWithin should be a number in milliseconds")
            if extra_params['commitWithin'] < 0:
                raise ValueError("commitWithin should be a number in milliseconds")
        if softCommit is not None:
            extra_params['softCommit'] = "true" if softCommit else "false"
        if optimize is not None:
            extra_params['optimize'] = "true" if optimize else "false"
        if waitSearcher is not None:
            extra_params['waitSearcher'] = "true" if waitSearcher else "false"
        if expungeDeletes is not None:
            extra_params['expungeDeletes'] = "true" if expungeDeletes else "false"
        if maxSegments is not None:
            try:
                extra_params['maxSegments'] = str(int(maxSegments))
            except (TypeError, ValueError):
                raise ValueError("maxSegments")
            if extra_params['maxSegments'] <= 0:
                raise ValueError("maxSegments should be a positive number")
        if 'expungeDeletes' in extra_params and 'commit' not in extra_params:
            raise ValueError("Can't do expungeDeletes without commit")
        if 'maxSegments' in extra_params and 'optimize' not in extra_params:
            raise ValueError("Can't do maxSegments without optimize")
        if extra_params:
            return "%s?%s" % (self.update_url, urllib.urlencode(sorted(extra_params.items())))
        else:
            return self.update_url

    def select(self, params):
        if not self.readable:
            raise TypeError("This Solr instance is only for writing")
        if self.format == 'json':
            params.append(('wt', 'json'))
        qs = urllib.urlencode(params)
        url = "%s?%s" % (self.select_url, qs)
        if len(url) > self.max_length_get_url:
            warnings.warn("Long query URL encountered - POSTing instead of "
                "GETting. This query will not be cached at the HTTP layer")
            url = self.select_url
            kwargs = dict(
                method="POST",
                body=qs,
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )
        else:
            kwargs = dict(method="GET")
        r, c = self.request(url, **kwargs)
        if r.status != 200:
            raise SolrError(r, c)
        return c

    def mlt(self, params, content=None):
        """Perform a MoreLikeThis query using the content specified
        There may be no content if stream.url is specified in the params.
        """
        if not self.readable:
            raise TypeError("This Solr instance is only for writing")
        qs = urllib.urlencode(params)
        base_url = "%s?%s" % (self.mlt_url, qs)
        if content is None:
            kwargs = {'uri': base_url, 'method': "GET"}
        else:
            get_url = "%s&stream.body=%s" % (base_url, urllib.quote_plus(content))
            if len(get_url) <= self.max_length_get_url:
                kwargs = {'uri': get_url, 'method': "GET"}
            else:
                kwargs = {'uri': base_url, 'method': "POST",
                    'body': content, 'headers': {"Content-Type": "text/plain; charset=utf-8"}}
        r, c = self.request(**kwargs)
        if r.status != 200:
            raise SolrError(r, c)
        return c


class SolrInterface(object):

    def __init__(self, url, schemadoc=None, http_connection=None, mode='', retry_timeout=-1,
            max_length_get_url=MAX_LENGTH_GET_URL, format='xml'):
        self.conn = SolrConnection(url, http_connection, mode, retry_timeout, max_length_get_url, format)
        self.schemadoc = schemadoc
        allowed_formats = ('xml', 'json')
        if format not in allowed_formats:
            raise ValueError("Unsupported format '%s': allowed are %s" %
                    (format, ','.join(allowed_formats)))
        self.format = format
        self.file_cache = {}
        self.init_schema()

    def make_file_url(self, filename):
        return urlparse.urljoin(self.conn.url, 'admin/file/?file=') + filename

    def get_file(self, filename):
        # return remote file as StringIO and cache the contents
        if filename not in self.file_cache:
            r, c = self.conn.request(self.make_file_url(filename))
            if r.status != 200:
                raise EnvironmentError("Couldn't retrieve schema document from server - received status code %s\n%s" % (r.status, c))
            self.file_cache[filename] = c
        return StringIO.StringIO(self.file_cache[filename])

    def save_file_cache(self, dirname):
        # take the file cache and save to a directory
        for filename in self.file_cache:
            open(path.join(dirname, filename), 'w').write(self.file_cache[filename])

    def get_xinclude_list_for_file(self, filename):
        # return a list of xinclude elements in this file
        tree = etree.parse(self.get_file(filename))
        return tree.getroot().findall('{http://www.w3.org/2001/XInclude}include')

    def get_file_and_included_files(self, filename):
        # return a list containing this file, and all files this file includes
        # via xinclude.  And do this recursively to ensure we have all we need.
        file_list = [filename]
        xinclude_list = self.get_xinclude_list_for_file(filename)
        for xinclude_node in xinclude_list:
            included_file = xinclude_node.get('href')
            file_list += self.get_file_and_included_files(included_file)
        return file_list

    def get_parsed_schema_file_with_xincludes(self, filename):
        # get the parsed schema file, and ensure we also get any files
        # required for any xinclude.  If an xinclude is required, we need
        # to save the files to the local disk before we call xinclude()
        try:
            file_list = self.get_file_and_included_files(filename)
            if len(file_list) == 1:
                # there are no xincludes, we can do this the easy way
                schemadoc = etree.parse(self.get_file(filename))
            else:
                # save all contents to files, then load from file and xinclude
                dirname = tempfile.mkdtemp()
                try:
                    self.save_file_cache(dirname)
                    schemadoc = etree.parse(path.join(dirname, filename))
                    schemadoc.xinclude()
                finally:
                    # delete dirname
                    shutil.rmtree(dirname)
        except etree.XMLSyntaxError, e:
            raise SolrError("Invalid XML in schema:\n%s" % e.args[0])
        return schemadoc

    def init_schema(self):
        if self.schemadoc:
            schemadoc = self.schemadoc
        else:
            schemadoc = self.get_parsed_schema_file_with_xincludes('schema.xml')
        self.schema = SolrSchema(schemadoc, format=self.format)

    def add(self, docs, chunk=100, **kwargs):
        if hasattr(docs, "items") or not hasattr(docs, "__iter__"):
            docs = [docs]
        # to avoid making messages too large, we break the message every
        # chunk docs.
        for doc_chunk in grouper(docs, chunk):
            update_message = self.schema.make_update(doc_chunk)
            self.conn.update(str(update_message), **kwargs)

    def delete(self, docs=None, queries=None, **kwargs):
        if not docs and not queries:
            raise SolrError("No docs or query specified for deletion")
        elif docs is not None and (hasattr(docs, "items") or not hasattr(docs, "__iter__")):
            docs = [docs]
        delete_message = self.schema.make_delete(docs, queries)
        self.conn.update(str(delete_message), **kwargs)

    def commit(self, *args, **kwargs):
        self.conn.commit(*args, **kwargs)

    def optimize(self, *args, **kwargs):
        self.conn.optimize(*args, **kwargs)

    def rollback(self):
        self.conn.rollback()

    def delete_all(self):
        # When deletion is fixed to escape query strings, this will need fixed.
        self.delete(queries=self.Q(**{"*":"*"}))

    def search(self, **kwargs):
        params = params_from_dict(**kwargs)
        return self.schema.parse_response(self.conn.select(params))

    def query(self, *args, **kwargs):
        q = SolrSearch(self)
        if len(args) + len(kwargs) > 0:
            return q.query(*args, **kwargs)
        else:
            return q

    def mlt_search(self, content=None, **kwargs):
        params = params_from_dict(**kwargs)
        return self.schema.parse_response(self.conn.mlt(params, content=content))

    def mlt_query(self, fields=None, content=None, content_charset=None, url=None, query_fields=None,
                  **kwargs):
        """Perform a similarity query on MoreLikeThisHandler

        The MoreLikeThisHandler is expected to be registered at the '/mlt'
        endpoint in the solrconfig.xml file of the server.

        fields is the list of field names to compute similarity upon. If not
        provided, we just use the default search field.
        query_fields can be used to adjust boosting values on a subset of those
        fields.

        Other MoreLikeThis specific parameters can be passed as kwargs without
        the 'mlt.' prefix.
        """
        q = MltSolrSearch(self, content=content, content_charset=content_charset, url=url)
        return q.mlt(fields=fields, query_fields=query_fields, **kwargs)

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
