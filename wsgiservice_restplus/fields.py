# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from calendar import timegm
from datetime import date, datetime
from decimal import Decimal, ROUND_HALF_EVEN
from email.utils import formatdate

from six import itervalues, text_type, string_types

from wsgiservice_restplus.errors import RestError
from wsgiservice_restplus.inputs import date_from_iso8601, datetime_from_iso8601, datetime_from_rfc822
from wsgiservice_restplus.utils import not_none
from wsgiservice_restplus.converters import Boolean as BooleanConverter


__all__ = ('Raw', 'String', 'FormattedString',
           'DateTime', 'Date',
           'Boolean', 'Integer', 'Float', 'Arbitrary', 'Fixed',
           'Nested', 'List', 'ClassName', 'Polymorph',
           'StringMixin', 'MinMaxMixin', 'NumberMixin', 'MarshallingError')


class MarshallingError(RestError):
    '''
    This is an encapsulating Exception in case of marshalling error.
    '''
    def __init__(self, underlying_exception):
        # just put the contextual representation of the error to hint on what
        # went wrong without exposing internals
        super(MarshallingError, self).__init__(text_type(underlying_exception))


def is_indexable_but_not_string(obj):
    return not hasattr(obj, "strip") and hasattr(obj, "__iter__")


def get_value(key, obj, default=None):
    '''Helper for pulling a keyed value off various types of objects'''
    if isinstance(key, int):
        return _get_value_for_key(key, obj, default)
    elif callable(key):
        return key(obj)
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
        except (IndexError, TypeError, KeyError):
            pass
    return getattr(obj, key, default)


def to_marshallable_type(obj):
    '''
    Helper for converting an object to a dictionary only if it is not
    dictionary already or an indexable object nor a simple type
    '''
    if obj is None:
        return None  # make it idempotent for None

    if hasattr(obj, '__marshallable__'):
        return obj.__marshallable__()

    if hasattr(obj, '__getitem__'):
        return obj  # it is indexable it is ok

    return dict(obj.__dict__)


def make_mandatory(field_obj):
    """Makes the field object mandatory - WIP """

    if hasattr(field_obj, 'valid_params'):
        field_obj.valid_params['mandatory'] = True
        return field_obj
    else:
        return field_obj


class Raw(object):
    '''
    Raw provides a base field class from which others should extend. It
    applies no formatting by default, and should only be used in cases where
    data does not need to be formatted before being serialized. Fields should
    throw a :class:`MarshallingError` in case of parsing problem.

    :param default: The default value for the field, if no value is
        specified.
    :param attribute: If the public facing value differs from the internal
        value, use this to retrieve a different attribute from the response
        than the publicly named value.
    :param str title: The field title (for documentation purpose)
    :param str description: The field description (for documentation purpose)
    :param bool required: Is the field mandatory?
    :param bool readonly: Is the field read only? (for documentation purpose)
    :param example: An optional data example (for documentation purpose)
    :param callable mask: An optional mask function to be applied to output
    '''
    #: The JSON/Swagger schema type
    __schema_type__ = 'object'
    #: The JSON/Swagger schema format
    __schema_format__ = None
    #: An optional JSON/Swagger schema example
    __schema_example__ = None

    def __init__(self, default=None, attribute=None, title=None, description=None,
                 mandatory=None, readonly=None, example=None, mask=None, **kwargs):
        self.attribute = attribute
        self.default = default
        self.title = title
        self.description = description
        self.required = mandatory
        self.readonly = readonly
        self.example = example or self.__schema_example__
        self.mask = mask

        self.valid_params = {
            "re": kwargs.get('re', None),
            "convert": kwargs.get('convert', None),
            "doc": self.description or None,
            "mandatory": kwargs.get('mandatory', False)
        }

    def format(self, value):
        '''
        Formats a field's value. No-op by default - field classes that
        modify how the value of existing object keys should be presented should
        override this and apply the appropriate formatting.

        :param value: The value to format
        :raises MarshallingError: In case of formatting problem

        Ex::

            class TitleCase(Raw):
                def format(self, value):
                    return unicode(value).title()
        '''
        return value

    def _v(self, key):
        '''Helper for getting a value from attribute allowing callable'''
        value = getattr(self, key)
        return value() if callable(value) else value

    # @cached_property
    @property # TODO: check vs. cached_property
    def __schema__(self):
        return not_none(self.schema())

    def schema(self):
        return {
            'type': self.__schema_type__,
            'format': self.__schema_format__,
            'title': self.title,
            'description': self.description,
            'readOnly': self.readonly,
            'default': self._v('default'),
            'example': self.example,
        }


class Nested(Raw):
    '''
    Allows you to nest one set of fields inside another.
    See :ref:`nested-field` for more information

    :param dict model: The model dictionary to nest
    :param bool allow_null: Whether to return None instead of a dictionary
        with null keys, if a nested dictionary has all-null keys
    :param kwargs: If ``default`` keyword argument is present, a nested
        dictionary will be marshaled as its value if nested dictionary is
        all-null keys (e.g. lets you return an empty JSON object instead of
        null)
    '''
    __schema_type__ = None

    def __init__(self, model, allow_null=False, as_list=False, **kwargs):
        self.model = model
        self.as_list = as_list
        self.allow_null = allow_null
        super(Nested, self).__init__(**kwargs)

    @property
    def nested(self):
        return getattr(self.model, 'resolved', self.model)

    def schema(self):
        schema = super(Nested, self).schema()
        ref = '#/definitions/{0}'.format(self.nested.name)

        if self.as_list:
            schema['type'] = 'array'
            schema['items'] = {'$ref': ref}
        else:
            schema['$ref'] = ref

        return schema

    def clone(self, mask=None):
        kwargs = self.__dict__.copy()
        model = kwargs.pop('model')
        if mask:
            model = mask.apply(model.resolved if hasattr(model, 'resolved') else model)
        return self.__class__(model, **kwargs)


class List(Raw):

    '''
    Field for marshalling lists of other fields.

    See :ref:`list-field` for more information.

    :param cls_or_instance: The field type the list will contain.
    '''

    def __init__(self, cls_or_instance, **kwargs):
        self.min_items = kwargs.pop('min_items', None)
        self.max_items = kwargs.pop('max_items', None)
        self.unique = kwargs.pop('unique', None)
        super(List, self).__init__(**kwargs)
        if not self.valid_params.get('convert'):
            self.valid_params['convert'] = list
        error_msg = 'The type of the list elements must be a subclass of fields.Raw'
        if isinstance(cls_or_instance, type):
            if not issubclass(cls_or_instance, Raw):
                raise MarshallingError(error_msg)
            self.container = cls_or_instance()
        else:
            if not isinstance(cls_or_instance, Raw):
                raise MarshallingError(error_msg)
            self.container = cls_or_instance

    def __iter__(self):

        return self.model

    def format(self, value):
        # Convert all instances in typed list to container type
        if isinstance(value, set):
            value = list(value)

        is_nested = isinstance(self.container, Nested) or type(self.container) is Raw

        def is_attr(val):
            return self.container.attribute and hasattr(val, self.container.attribute)

        return [
            self.container.output(idx,
                val if (isinstance(val, dict) or is_attr(val)) and not is_nested else value)
            for idx, val in enumerate(value)
        ]

    def schema(self):
        schema = super(List, self).schema()
        schema.update(minItems=self._v('min_items'),
                      maxItems=self._v('max_items'),
                      uniqueItems=self._v('unique'))
        schema['type'] = 'array'
        schema['items'] = self.container.__schema__
        return schema

    def clone(self, mask=None):
        kwargs = self.__dict__.copy()
        model = kwargs.pop('container')
        if mask:
            model = mask.apply(model)
        return self.__class__(model, **kwargs)


class StringMixin(object):
    __schema_type__ = 'string'

    def __init__(self, *args, **kwargs):
        self.min_length = kwargs.pop('min_length', None)
        self.max_length = kwargs.pop('max_length', None)
        self.pattern = kwargs.pop('pattern', None)
        super(StringMixin, self).__init__(*args, **kwargs)
        if not self.valid_params.get('convert'):
            self.valid_params['convert'] = str

    def schema(self):
        schema = super(StringMixin, self).schema()
        schema.update(minLength=self._v('min_length'),
                      maxLength=self._v('max_length'),
                      pattern=self._v('pattern'))
        return schema


class MinMaxMixin(object):
    def __init__(self, *args, **kwargs):
        self.minimum = kwargs.pop('min', None)
        self.excluisveMinimum = kwargs.pop('exclusiveMin', None)
        self.maximum = kwargs.pop('max', None)
        self.exclusiveMaximum = kwargs.pop('exclusiveMax', None)
        super(MinMaxMixin, self).__init__(*args, **kwargs)

    def schema(self):
        schema = super(MinMaxMixin, self).schema()
        schema.update(minimum=self._v('minimum'),
                      exclusiveMinimum=self._v('excluisveMinimum'),
                      maximum=self._v('maximum'),
                      exclusiveMaximum=self._v('exclusiveMaximum'))
        return schema


class NumberMixin(MinMaxMixin):
    __schema_type__ = 'number'

    def __init__(self, *args, **kwargs):
        self.multiple = kwargs.pop('multiple', None)
        super(NumberMixin, self).__init__(*args, **kwargs)

    def schema(self):
        schema = super(NumberMixin, self).schema()
        schema.update(multipleOf=self._v('multiple'))
        return schema


class String(StringMixin, Raw):
    '''
    Marshal a value as a string. Uses ``six.text_type`` so values will
    be converted to :class:`unicode` in python2 and :class:`str` in
    python3.
    '''
    def __init__(self, *args, **kwargs):
        self.enum = kwargs.pop('enum', None)
        self.discriminator = kwargs.pop('discriminator', None)
        super(String, self).__init__(*args, **kwargs)
        self.required = self.discriminator or self.required
        if not self.valid_params.get('convert'):
            self.valid_params['convert'] = str

    def format(self, value):
        try:
            return text_type(value)
        except ValueError as ve:
            raise MarshallingError(ve)

    def schema(self):
        enum = self._v('enum')
        schema = super(String, self).schema()
        schema.update(enum=enum)
        if enum and schema['example'] is None:
            schema['example'] = enum[0]
        return schema


class Integer(NumberMixin, Raw):
    '''
    Field for outputting an integer value.

    :param int default: The default value for the field, if no value is specified.
    '''
    __schema_type__ = 'integer'

    def __init__(self, *args, **kwargs):
        super(Integer, self).__init__(*args, **kwargs)
        if not self.valid_params.get('convert'):
            self.valid_params['convert'] = int

    def format(self, value):
        try:
            if value is None:
                return self.default
            return int(value)
        except ValueError as ve:
            raise MarshallingError(ve)


class Float(NumberMixin, Raw):
    '''
    A double as IEEE-754 double precision.

    ex : 3.141592653589793 3.1415926535897933e-06 3.141592653589793e+24 nan inf -inf
    '''

    def __init__(self, *args, **kwargs):
        super(Float, self).__init__(*args, **kwargs)
        if not self.valid_params.get('convert'):
            self.valid_params['convert'] = float

    def format(self, value):
        try:
            return float(value)
        except ValueError as ve:
            raise MarshallingError(ve)


class Arbitrary(NumberMixin, Raw):
    '''
    A floating point number with an arbitrary precision.

    ex: 634271127864378216478362784632784678324.23432
    '''

    def format(self, value):
        return text_type(Decimal(value))


ZERO = Decimal()


class Fixed(NumberMixin, Raw):
    '''
    A decimal number with a fixed precision.
    '''
    def __init__(self, decimals=5, **kwargs):
        super(Fixed, self).__init__(**kwargs)
        self.precision = Decimal('0.' + '0' * (decimals - 1) + '1')

    def format(self, value):
        dvalue = Decimal(value)
        if not dvalue.is_normal() and dvalue != ZERO:
            raise MarshallingError('Invalid Fixed precision number.')
        return text_type(dvalue.quantize(self.precision, rounding=ROUND_HALF_EVEN))


class Boolean(Raw):
    '''
    Field for outputting a boolean value.

    Empty collections such as ``""``, ``{}``, ``[]``, etc. will be converted to ``False``.
    '''
    __schema_type__ = 'boolean'

    def __init__(self, *args, **kwargs):
        super(Boolean, self).__init__(*args, **kwargs)
        if not self.valid_params.get('convert'):
            self.valid_params['convert'] = BooleanConverter

    def format(self, value):
        return bool(value)


class DateTime(MinMaxMixin, Raw):
    '''
    Return a formatted datetime string in UTC. Supported formats are RFC 822 and ISO 8601.

    See :func:`email.utils.formatdate` for more info on the RFC 822 format.

    See :meth:`datetime.datetime.isoformat` for more info on the ISO 8601 format.

    :param str dt_format: ``rfc822`` or ``iso8601``
    '''
    __schema_type__ = 'string'
    __schema_format__ = 'date-time'

    def __init__(self, dt_format='iso8601', **kwargs):
        super(DateTime, self).__init__(**kwargs)
        self.dt_format = dt_format
        if not self.valid_params.get('convert'):
            self.valid_params['convert'] = str

    def parse(self, value):
        if value is None:
            return None
        elif isinstance(value, string_types):
            parser = datetime_from_iso8601 if self.dt_format == 'iso8601' else datetime_from_rfc822
            return parser(value)
        elif isinstance(value, datetime):
            return value
        elif isinstance(value, date):
            return datetime(value.year, value.month, value.day)
        else:
            raise ValueError('Unsupported DateTime format')

    def format(self, value):
        try:
            value = self.parse(value)
            if self.dt_format == 'iso8601':
                return self.format_iso8601(value)
            elif self.dt_format == 'rfc822':
                return self.format_rfc822(value)
            else:
                raise MarshallingError(
                    'Unsupported date format %s' % self.dt_format
                )
        except (AttributeError, ValueError) as e:
            raise MarshallingError(e)

    def format_rfc822(self, dt):
        '''
        Turn a datetime object into a formatted date.

        :param datetime dt: The datetime to transform
        :return: A RFC 822 formatted date string
        '''
        return formatdate(timegm(dt.utctimetuple()))

    def format_iso8601(self, dt):
        '''
        Turn a datetime object into an ISO8601 formatted date.

        :param datetime dt: The datetime to transform
        :return: A ISO 8601 formatted date string
        '''
        return dt.isoformat()

    def _for_schema(self, name):
        value = self.parse(self._v(name))
        return self.format(value) if value else None

    def schema(self):
        schema = super(DateTime, self).schema()
        schema['default'] = self._for_schema('default')
        schema['minimum'] = self._for_schema('minimum')
        schema['maximum'] = self._for_schema('maximum')
        return schema


class Date(DateTime):
    '''
    Return a formatted date string in UTC in ISO 8601.

    See :meth:`datetime.date.isoformat` for more info on the ISO 8601 format.
    '''
    __schema_format__ = 'date'

    def __init__(self, **kwargs):
        kwargs.pop('dt_format', None)
        super(Date, self).__init__(dt_format='iso8601', **kwargs)
        if not self.valid_params.get('convert'):
            self.valid_params['convert'] = str

    def parse(self, value):
        if value is None:
            return None
        elif isinstance(value, string_types):
            return date_from_iso8601(value)
        elif isinstance(value, datetime):
            return value.date()
        elif isinstance(value, date):
            return value
        else:
            raise ValueError('Unsupported Date format')


### URL resource
# TODO: Adapt this to wsgiservice e.g. using the url_for implemented in the Api class
class Url(StringMixin, Raw):
    '''
    A string representation of a Url

    :param str endpoint: Endpoint name. If endpoint is ``None``, ``request.endpoint`` is used instead
    :param bool absolute: If ``True``, ensures that the generated urls will have the hostname included
    :param str scheme: URL scheme specifier (e.g. ``http``, ``https``)
    '''
    def __init__(self, endpoint=None, absolute=False, scheme=None, **kwargs):
        super(Url, self).__init__(**kwargs)
        self.endpoint = endpoint
        self.absolute = absolute
        self.scheme = scheme

        if not self.valid_params.get('convert'):
            self.valid_params['convert'] = str


class FormattedString(StringMixin, Raw):
    '''
    FormattedString is used to interpolate other values from
    the response into this field. The syntax for the source string is
    the same as the string :meth:`~str.format` method from the python
    stdlib.

    Ex::

        fields = {
            'name': fields.String,
            'greeting': fields.FormattedString("Hello {name}")
        }
        data = {
            'name': 'Doug',
        }
        marshal(data, fields)

    :param str src_str: the string to format with the other values from the response.
    '''
    def __init__(self, src_str, **kwargs):
        super(FormattedString, self).__init__(**kwargs)
        self.src_str = text_type(src_str)


class ClassName(String):
    '''
    Return the serialized object class name as string.

    :param bool dash: If `True`, transform CamelCase to kebab_case.
    '''
    def __init__(self, dash=False, **kwargs):
        super(ClassName, self).__init__(**kwargs)
        self.dash = dash


class Polymorph(Nested):
    '''
    A Nested field handling inheritance.

    Allows you to specify a mapping between Python classes and fields specifications.

    .. code-block:: python

        mapping = {
            Child1: child1_fields,
            Child2: child2_fields,
        }

        fields = api.model('Thing', {
            owner: fields.Polymorph(mapping)
        })

    :param dict mapping: Maps classes to their model/fields representation
    '''
    def __init__(self, mapping, mandatory=False, **kwargs):
        self.mapping = mapping
        parent = self.resolve_ancestor(list(itervalues(mapping)))
        super(Polymorph, self).__init__(parent, allow_null=not mandatory, **kwargs)


    def resolve_ancestor(self, models):
        '''
        Resolve the common ancestor for all models.

        Assume there is only one common ancestor.
        '''
        ancestors = [m.ancestors for m in models]
        candidates = set.intersection(*ancestors)
        if len(candidates) != 1:
            field_names = [f.name for f in models]
            raise ValueError('Unable to determine the common ancestor for: ' + ', '.join(field_names))

        parent_name = candidates.pop()
        return models[0].get_parent(parent_name)

    def clone(self, mask=None):
        data = self.__dict__.copy()
        mapping = data.pop('mapping')
        for field in ('allow_null', 'model'):
            data.pop(field, None)

        data['mask'] = mask
        return Polymorph(mapping, **data)
