# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import re

from collections import OrderedDict
from copy import deepcopy
from six.moves.urllib.parse import quote

from six import iteritems


FIRST_CAP_RE = re.compile('(.)([A-Z][a-z]+)')
ALL_CAP_RE = re.compile('([a-z0-9])([A-Z])')

__all__ = ('merge', 'camel_to_dash', 'default_id', 'not_none', 'not_none_sorted', 'format_definition_reference', 'format_definition_key')


def merge(first, second):
    '''
    Recursively merges two dictionnaries.

    Second dictionnary values will take precedance over those from the first one.
    Nested dictionnaries are merged too.

    :param dict first: The first dictionnary
    :param dict second: The second dictionnary
    :return: the resulting merged dictionnary
    :rtype: dict
    '''
    if not isinstance(second, dict):
        return second
    result = deepcopy(first)
    for key, value in iteritems(second):
        if key in result and isinstance(result[key], dict):
                result[key] = merge(result[key], value)
        else:
            result[key] = deepcopy(value)
    return result


def camel_to_dash(value):
    '''
    Transform a CamelCase string into a low_dashed one

    :param str value: a CamelCase string to transform
    :return: the low_dashed string
    :rtype: str
    '''
    first_cap = FIRST_CAP_RE.sub(r'\1_\2', value)
    return ALL_CAP_RE.sub(r'\1_\2', first_cap).lower()


def default_id(resource, method):
    '''Default operation ID generator'''
    return '{0}_{1}'.format(method, camel_to_dash(resource))


def not_none(data):
    '''
    Remove all keys where value is None

    :param dict data: A dictionnary with potentialy some values set to None
    :return: The same dictionnary without the keys with values to ``None``
    :rtype: dict
    '''
    return dict((k, v) for k, v in iteritems(data) if v is not None)


def not_none_sorted(data):
    '''
    Remove all keys where value is None

    :param OrderedDict data: A dictionnary with potentialy some values set to None
    :return: The same dictionnary without the keys with values to ``None``
    :rtype: OrderedDict
    '''
    ordered_items = OrderedDict(sorted(iteritems(data)))
    return OrderedDict((k, v) for k, v in iteritems(ordered_items) if v is not None)


def str_to_pascal_case(s):
    words = s.split(' ')
    return ''.join([word.capitalize() for word in words])


def format_definition_reference(definition_name):
    """
    JSON reference is an URI ( see: https://tools.ietf.org/html/draft-pbryan-zyp-json-ref-03#section-3)
    which according to specs ( https://tools.ietf.org/html/rfc3986#section-2.4 ) requires
    all special characters to be percent-encoded.
    This standard is unfortunately not followed by some OpenAPI docs consumers
    (like Stoplight or older Swagger UI versions).
    For that reason we're making all model keys PascalCase so there's no need to encode space as '%20'
    (being the only special character that we're using so far) which can be misinterpreted.
    """
    return '#/definitions/{0}'.format(quote(format_definition_key(definition_name)))


def format_definition_key(definition_name):
    """See format_definition_reference function description for context"""
    return str_to_pascal_case(definition_name)
