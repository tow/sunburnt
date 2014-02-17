import socket

try:
    import requests
    httplib2 = None
except ImportError:
    requests = None
    try:
        import httplib2
    except ImportError:
        raise ImportError('No module named requests or httplib2')


ConnectionError = requests.exceptions.ConnectionError if requests else socket.error


def wrap_http_connection(http_connection=None):
    if not http_connection:
        http_connection = requests.Session() if requests else httplib2.Http()
    if not is_requests_instance(http_connection):
        http_connection = RequestWrapper(http_connection)
    return http_connection


def is_requests_instance(obj):
    return hasattr(obj, 'get') and hasattr(obj, 'post')


class RequestWrapper(object):
    """
    Wraps an `httplib2` instance to make it behave enough like a
    `requests` instance for our purposes
    """
    def __init__(self, conn):
        self.conn = conn

    def request(self, method, url, data=None, headers=None):
        response, content = self.conn.request(url, method=method, body=data, headers=headers)
        return ResponseWrapper(response, content)


class ResponseWrapper(object):
    """
    Wraps an `httplib2` response pair to make it behave enough like a
    `requests` response object for our purposes
    """
    def __init__(self, response, content):
        self.status_code = response.status
        self.content = content

