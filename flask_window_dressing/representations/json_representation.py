from __future__ import absolute_import
from flask import make_response, current_app
from json import dumps, loads

from . import ResourceRepresentation


class JsonResource(ResourceRepresentation):
    content_type = 'application/json'

    def output(self, data, code, headers=None):
        # This dictionary contains any kwargs that are to be passed to the json.dumps
        # function, used below.
        settings = {}

        # If we're in debug mode, and the indent is not set, we set it to a
        # reasonable value here.  Note that this won't override any existing value
        # that was set.  We also set the "sort_keys" value.
        local_settings = settings.copy()
        if current_app.debug:
            local_settings.setdefault('indent', 4)
            local_settings.setdefault('sort_keys', True)

        # We also add a trailing newline to the dumped JSON if the indent value is
        # set - this makes using `curl` on the command line much nicer.
        dumped = dumps(data, **local_settings)
        if 'indent' in local_settings:
            dumped += '\n'

        response = make_response(dumped, code)
        if headers:
            headers.extend({'Content-Type': self.content_type})
        else:
            headers = {'Content-Type': self.content_type}
        response.headers.extend(headers)

        return response


    def input(self, data):
        loaded = loads(data)
        
        return loaded


class HtmlResource(ResourceRepresentation):
    content_type = 'text/html'

    def output(self, data, code, headers=None):
        if data and (isinstance(data, list) and isinstance(data[0], dict)) \
            or isinstance(data, dict):
            # Output as JSON, because marshaled stuff won't work with
            # make_response. This is used so that we can view the json response
            # with a normal browser request
            response = HtmlResource().output(data, code, headers)
        else:
            response = make_response(data, code)
            if headers:
                headers.extend({'Content-Type': self.content_type})
            else:
                headers = {'Content-Type': self.content_type}
            response.headers.extend(headers)

        return response

    def input(self, data):
        return data
