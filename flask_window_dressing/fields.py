from decimal import Decimal as MyDecimal, ROUND_HALF_EVEN
from dateutil import parser
import pytz
import six
try:
    from urlparse import urlparse, urlunparse
except ImportError:
    # python3
    from urllib.parse import urlparse, urlunparse
from flask import url_for

from . import marshal

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

class MarshallingException(Exception):
    """
    This is an encapsulating Exception in case of marshalling error.
    """

    def __init__(self, underlying_exception):
        # just put the contextual representation of the error to hint on what
        # went wrong without exposing internals
        super(MarshallingException, self).__init__(six.text_type(underlying_exception))


def is_indexable_but_not_string(obj):
    return not hasattr(obj, "strip") and hasattr(obj, "__getitem__")


def get_value(key, obj, default=None):
    """Helper for pulling a keyed value off various types of objects"""
    if type(key) == int:
        return _get_value_for_key(key, obj, default)
    else:
        return _get_value_for_keys(key.split('.'), obj, default)


def _get_value_for_keys(keys, obj, default):
    if len(keys) == 1:
        return _get_value_for_key(keys[0], obj, default)
    else:
        return _get_value_for_keys(
            keys[1:], _get_value_for_key(keys[0], obj, default), default)


def _get_value_for_key(key, obj, default):
    if is_indexable_but_not_string(obj):
        try:
            return obj[key]
        except KeyError:
            return default
    if hasattr(obj, key):
        return getattr(obj, key)
    return default


def to_marshallable_type(obj):
    """
    Helper for converting an object to a dictionary only if it is not
    dictionary already or an indexable object nor a simple type
    """
    if obj is None:
        return None  # make it idempotent for None

    if hasattr(obj, '__getitem__'):
        return obj  # it is indexable it is ok

    if hasattr(obj, '__marshallable__'):
        return obj.__marshallable__()

    return dict(obj.__dict__)


class Raw(object):
    """
    Raw provides a base field class from which others should extend. It
    applies no formatting by default, and should only be used in cases where
    data does not need to be formatted before being serialized. Fields should
    throw a MarshallingException in case of parsing problem.
    """
    def __init__(self, default=None, attribute=None, input_required=False, validate=None):
        """
        :param default: (optional) A static default value or function that creates a default
            value based off of passed in values. The default function is called with the specific
            field key and the local field object as well as the full data of all the fields currently
            being marshaled. The function needs to return a default value that conforms to the field 
            definition.
        :param attribute: (optional) The name of the field in the internal representation
        :param input_required: (optional, default:False) If set to True, the fields is required for the 
            incoming request to be successfully marshaled.
        :param validate: (optional) A function that validates the data provided. The default function 
            is called with the specific field key and the local field object as well as the full data of 
            all the fields currently being marshaled. The function needs to return True or False.
        """
        self.attribute = attribute
        self.default = default
        self.input_required = input_required
        self.validate = validate

    def format(self, value):
        """
        Formats a field's value. No-op by default, concrete fields should
        override this and apply the appropriate formatting.

        :param value: The value to format
        :exception MarshallingException: In case of formatting problem

        Ex::

            class TitleCase(Raw):
                def format(self, value):
                    return unicode(value).title()
        """
        return value

    def output(self, key, obj, full_data):
        """
        This function takes an internal representation and applies the marshaling
        rules to create the external representation.

        Pulls the value for the given key from the object. Then applies the
        field's default function (or static value) and a validation function, if
        provided, followed by the formatting and returns the result.

        :param key: The field representation key
        :param obj: The local data object to pull the value from
        :param full_data: The full data object with all fields
        :exception MarshallingException: In case of formatting problem
        """
        value = get_value(key if self.attribute is None else self.attribute, obj)

        if value is None:
            if hasattr(self.default, '__call__'):
                return self.default(key, obj, full_data)
            return self.default

        if self.validate:
            if not hasattr(self.validate, '__call__'):
                raise MarshallingException('validate for field {} is not a function'.format(key))
            value = self.validate(key, obj, full_data)

        return self.format(value)

    def input(self, key, obj, full_data):
        """
        This function takes an external representation and applies the marshaling
        rules to create the internal representation.

        Pulls the value for the given key from the object and checks for all required fields.
        Then applies the field's default function (or static value) and a validation function, if
        provided, followed by the formatting and returns the result.
        
        :param key: The field representation key
        :param obj: The local data object to pull the value from
        :param full_data: The full data object with all fields
        :exception MarshallingException: In case of formatting problem
        """
        value = get_value(key, obj)
        if value is None:
            if self.input_required == True:
                raise MarshallingException("The field {} is required for requests".format(key))
            if hasattr(self.default, '__call__'):
                return self.default(key, obj, full_data)
            return self.default

        if self.validate:
            if not hasattr(self.validate, '__call__'):
                raise MarshallingException('validate for field {} is not a function'.format(key))
            value = self.validate(key, obj, full_data)

        return self.format(value)


class Nested(Raw):
    """
    Allows you to nest one set of fields inside another.
    See :ref:`nested-field` for more information

    :param dict nested: The dictionary to nest
    :param bool allow_null: Whether to return None instead of a dictionary
        with null keys, if a nested dictionary has all-null keys
    """

    def __init__(self, nested, allow_null=False, **kwargs):
        self.nested = nested
        self.allow_null = allow_null
        super(Nested, self).__init__(**kwargs)

    def output(self, key, obj):
        value = get_value(key if self.attribute is None else self.attribute, obj)
        if self.allow_null and value is None:
            return None

        return marshal(value, self.nested)

    def input(self, key, obj):
        value = get_value(key, obj)
        if self.allow_null and value is None:
            return None

        return marshal(value, self.nested, True)


class List(Raw):
    def __init__(self, cls_or_instance, **kwargs):
        super(List, self).__init__(**kwargs)
        if isinstance(cls_or_instance, type):
            if not issubclass(cls_or_instance, Raw):
                raise MarshallingException("The type of the list elements "
                                           "must be a subclass of "
                                           "flask_restful.fields.Raw")
            self.container = cls_or_instance()
        else:
            if not isinstance(cls_or_instance, Raw):
                raise MarshallingException("The instances of the list "
                                           "elements must be of type "
                                           "flask_restful.fields.Raw")
            self.container = cls_or_instance

    def output(self, key, data, full_data):
        value = get_value(key if self.attribute is None else self.attribute, data)
        if value is None:
            if hasattr(self.default, '__call__'):
                return self.default(key, data, full_data)
            return self.default

        # we cannot really test for external dict behavior
        if is_indexable_but_not_string(value) and not isinstance(value, dict):
            # Convert all instances in typed list to container type
            return [self.container.output(idx, value, full_data) for idx, val
                    in enumerate(value)]

        return [marshal(value, self.container.nested)]

    def input(self, key, data, full_data):
        value = get_value(key, data)
        if value is None:
            if hasattr(self.default, '__call__'):
                return self.default(key, data, full_data)
            return self.default

        # we cannot really test for external dict behavior
        if is_indexable_but_not_string(value) and not isinstance(value, dict):
            # Convert all instances in typed list to container type
            return [self.container.input(idx, value, full_data) for idx, val
                    in enumerate(value)]

        return [marshal(value, self.container.nested)]


class String(Raw):
    def format(self, value):
        try:
            return six.text_type(value)
        except ValueError as ve:
            raise MarshallingException(ve)


class Integer(Raw):
    def __init__(self, default=0, **kwargs):
        super(Integer, self).__init__(default, **kwargs)

    def format(self, value):
        try:
            if value is None:
                return self.default
            return int(value)
        except ValueError as ve:
            raise MarshallingException(ve)


class Boolean(Raw):
    def format(self, value):
        return bool(value)


class FormattedString(Raw):
    def __init__(self, src_str):
        super(FormattedString, self).__init__()
        self.src_str = six.text_type(src_str)

    def output(self, key, obj, full_data):
        try:
            data = to_marshallable_type(obj)
            return self.src_str.format(**data)
        except (TypeError, IndexError) as error:
            raise MarshallingException(error)


class Url(Raw):
    """
    A string representation of a Url
    """
    def __init__(self, endpoint):
        super(Url, self).__init__()
        self.endpoint = endpoint

    def output(self, key, obj, full_data):
        try:
            data = to_marshallable_type(obj)
            o = urlparse(url_for(self.endpoint, **data))
            return urlunparse(("", "", o.path, "", "", ""))
        except TypeError as te:
            raise MarshallingException(te)


class Float(Raw):
    """
    A double as IEEE-754 double precision.
    ex : 3.141592653589793 3.1415926535897933e-06 3.141592653589793e+24 nan inf -inf
    """

    def format(self, value):
        try:
            return repr(float(value))
        except ValueError as ve:
            raise MarshallingException(ve)


class Arbitrary(Raw):
    """
        A floating point number with an arbitrary precision
          ex: 634271127864378216478362784632784678324.23432
    """

    def format(self, value):
        return six.text_type(MyDecimal(value))


class DateTime(Raw):
    """
    Return a ISO-formatted datetime string in UTC
    """
    def format(self, value):
        try:
            return value.isoformat()
        except AttributeError as ae:
            raise MarshallingException(ae)

    def input(self, key, obj):
        value = get_value(key, obj)
        if value:
            datetime = parser.parse(value).astimezone(pytz.utc)

        return datetime if value else None

ZERO = MyDecimal()


class Fixed(Raw):
    def __init__(self, decimals=5, **kwargs):
        super(Fixed, self).__init__(**kwargs)
        self.precision = MyDecimal('0.' + '0' * (decimals - 1) + '1')

    def format(self, value):
        dvalue = MyDecimal(value)
        if not dvalue.is_normal() and dvalue != ZERO:
            raise MarshallingException('Invalid Fixed precision number.')
        return six.text_type(dvalue.quantize(self.precision, rounding=ROUND_HALF_EVEN))

Price = Fixed

class Capitalize(Raw):
    """
    Capitalizes the first letter of the string
    """
    def format(self, value):
        return str(value).capitalize()

class CommaSeparatedList(List):
    """
    Takes a comma separated string in the request and transforms it to a list.
    A list in the response is converted to a comma separated string.
    """
    def output(self, key, data, full_data):
        value = get_value(key if self.attribute is None else self.attribute, data)
        if value is None:
            if hasattr(self.default, '__call__'):
                return self.default(key, data, full_data)
            return self.default

        if is_indexable_but_not_string(value) and not isinstance(value, dict):
            # Convert all instances in typed list to container type
            return ','.join(self.container.output(idx, value, full_data) for idx, val
                            in enumerate(value))

        if self.validate:
            if not hasattr(self.validate, '__call__'):
                raise MarshallingException('validate for field {} is not a function'.format(key))
            value = self.validate(key, data, full_data)

        return ','.join(marshal(value, self.container.nested))

    def input(self, key, data, full_data):
        value = get_value(key, data)
        if value is None:
            if hasattr(self.default, '__call__'):
                return self.default(key, data, full_data)
            return self.default

        # Split comma separated string and make a list
        value = value.split(',')
        if is_indexable_but_not_string(value) and not isinstance(value, dict):
            # Convert all instances in typed list to container type
            return [self.container.input(idx, value, full_data) for idx, val
                    in enumerate(value)]

        if self.validate:
            if not hasattr(self.validate, '__call__'):
                raise MarshallingException('validate for field {} is not a function'.format(key))
            value = self.validate(key, data, full_data)

        return [marshal(value, self.container.nested)]
