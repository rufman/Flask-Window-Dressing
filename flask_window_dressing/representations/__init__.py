from flask import make_response

class ResourceRepresentation(object):
    content_type = 'text/html'

    def output(self, data, code, headers=None):
        response = make_response(data, code)
        if headers:
            headers.extend({'Content-Type': self.content_type})
        else:
            headers = {'Content-Type': self.content_type}
        response.headers.extend(headers)

        return response

    def input(self, data):
        return data
