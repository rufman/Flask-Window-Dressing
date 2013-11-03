"""
    Flask-Window-Dressing
    ------------

    Window dressing for flask apps. Adds support for serializing responses
    and deserializing requests (marshaling). Also adds support for different
    resource representations.

    :copyright: (c) 2013 by Stephane Rufer.
    :license: MIT, see LICENSE for more details.
"""

__version__ = "0.1.0"

import functools
from flask import request
from .utils import unpack
from .representations.zefr_representation import JsonResource

try:
    #noinspection PyUnresolvedReferences
    from collections import OrderedDict
except ImportError:
    from .utils.ordereddict import OrderedDict

##
# This source is based off of flask-restful
# Copyright (c) 2013, Twilio, Inc.
# All rights reserved.

# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:

# - Redistributions of source code must retain the above copyright notice, this
#   list of conditions and the following disclaimer. 
# - Redistributions in binary form must reproduce the above copyright notice,
#   this list of conditions and the following disclaimer in the documentation
#   and/or other materials provided with the distribution.
# - Neither the name of the Twilio, Inc. nor the names of its contributors may be
#   used to endorse or promote products derived from this software without
#   specific prior written permission.

# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND
# ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
# DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE
# FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL
# DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR
# SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER
# CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY,
# OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

def marshal(data, full_data, fields, going_in=False):
    """
    Takes raw data (in the form of a dict, list, object) and a dict of
    fields that defines the representation of the data. It transforms an internal
    representation to the external one and vice versa. It also takes the full
    request or response data and a flag that indicates if we are marshaling a request
    (external to internal representation) or a response (internal to external).

    :param fields: a dict of whose keys will make up the final serialized
                   response output or internal request representation
    :param data: the actual object(s) from which the fields are taken from
    :param full_data: the full data in the request or the response
    :param going_in: (optional, default:False) If True we are marshaling an incoming request
        to the internal representation. If False we are marshaling a response to the external
        representation.
    """
    def make(cls):
        if isinstance(cls, type):
            return cls()
        return cls

    if isinstance(data, (list, tuple)):
        return [marshal(d, data, fields, going_in) for d in data]

    if going_in:
        items = ((k, marshal(data, full_data, v, True)) if isinstance(v, dict)
                                  else (k if not hasattr(v, 'attribute') else v.attribute 
                                  if v.attribute else k, make(v).input(k, data, full_data))
                                  for k, v in fields.items())
        resp = dict(items)
    else:
        items = ((k, marshal(data, full_data, v, False) if isinstance(v, dict)
                                  else make(v).output(k, data, full_data))
                                  for k, v in fields.items())
        resp = OrderedDict(items)

    return resp


class validate_params(object):
    def __init__(self, fields):
        """
        :param fields: A dict of whose keys will make up the final
            deserialization and validated request arguments representation.
        """
        self.fields = fields

    def __call__(self, f):
        @functools.wraps(f)
        def wrapper(*args, **kwargs):
            params = request.args
            if params:
                query_args = marshal(params, params, self.fields, going_in=True)
                kwargs.update(query_args)

            return f(*args, **kwargs)
        return wrapper


class marshal_with(object):
    """
    A decorator that marshals requests and responses coming from view methods.
    Incoming marshaling is applied before your view function is called and after
    then again after your function returns data. 

    NOTE: Because this decorator is applied on the way in an out, it needs to be the
    last in the list of all decorators applied to your function, unless you want to 
    manipulate the marshaled response emitted by this function.
    """
    def __init__(self, fields, representations=[]):
        """
        :param fields: A dict of whose keys will make up the final
            deserialization request input or serialized response output.
        :param representations: (optional) A list of resource representations
            that specify how the incoming request should be deserialization. If no 
            representations are provided the default is to apply json deserialization.
        """
        self.fields = fields
        self.representations = representations

    def __call__(self, f):
        @functools.wraps(f)
        def wrapper(*args, **kwargs):
            data = request.data
            if data:
                if not isinstance(data, dict):
                    if request.headers.has_key('Content-Type'):
                        request_representation = request.headers['Content-Type']
                        if request_representation == '' or 'application/json':
                            default_representation = JsonResource()
                            data = default_representation.input(data)
                        elif request_representation in self.representations.keys():
                            data = self.representations[request_representation].input(data)
                fields = marshal(data, data, self.fields, going_in=True)
                kwargs.update({'fields': fields})

            response = f(*args, **kwargs)
            if isinstance(response, tuple):
                data, code, headers = unpack(response)
                return marshal(data, data, self.fields), code, headers
            else:
                return marshal(response, response, self.fields)
        return wrapper
