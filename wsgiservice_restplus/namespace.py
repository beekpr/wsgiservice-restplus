# -*- coding: utf-8 -*-
from __future__ import unicode_literals, absolute_import

import inspect
import six
import warnings

from inspect import isclass
from wsgiservice_restplus.model import Model
from wsgiservice_restplus.utils import merge

from wsgiservice_restplus.wsgiservice_adaptors import get_resource_http_methods


class Namespace(object):
    """Groups resources together.Namespace is to API what :class:`flask:flask.Blueprint`
    is for :class:`flask:flask.Flask`.

    :param str name: The namespace name
    :param str description: An optionale short description
    :param str path: An optional prefix path. If not provided, prefix is ``/+name``
    :param list decorators: A list of decorators to apply to each resources
    :param bool validate: Whether or not to perform validation on this namespace
    :param Api api: an optional API to attache to the namespace
    :param bool public: Flags the namespace as public (when public=False, Api will hide this
    resource from swagger.json unless its retrieved via interna=true query parameter.)
    """

    def __init__(self, name, description=None, path='/', decorators=None, validate=None, **kwargs):

        self.name = name
        self.description = description
        self.path = path.rstrip('/') + '/' if path else ('/' + name + '/')
        self._validate = validate
        self.models = {}
        self.decorators = decorators if decorators else []
        self.resources = []
        self.apis = []
        self.public = kwargs.get('public', False)

        if 'api' in kwargs:
            self.apis.append(kwargs['api'])

    def add_resource(self, resource, url, **kwargs):
        """
        Register a Resource for a given API Namespace

        :param Resource resource: the resource ro register
        :param str urls: one or more url routes to match for the resource,standard flask routing rules apply.\
        Any url variables will be passed to the resource method as args.
        :param str endpoint: endpoint name (defaults to :meth:`Resource.__name__.lower`. Can be used to \
        reference this route in :class:`fields.Url` fields
        :param list|tuple resource_class_args: args to be forwarded to the constructor of the resource.
        :param dict resource_class_kwargs: kwargs to be forwarded to the constructor of the resource.

        Examples::
            namespace.add_resource(HelloWorld, '/', '/hello')
            namespace.add_resource(Foo, '/foo', endpoint="foo")
            namespace.add_resource(FooSpecial, '/special/foo', endpoint="foo")
        """
        resource.public = kwargs.get('public', False)

        self.resources.append((resource, url, kwargs))
        for api in self.apis:
            api.register_resource(self, resource, url, **kwargs)

    def route(self, url, **kwargs):
        """ A decorator to route resources. """
        if url[0] != '/':
            raise ValueError
        if len(url) > 1:
            url = self.path.rstrip('/') + url
        elif len(self.path) > 1:
            url = self.path.rstrip('/')
        else:
            url = self.path

        def wrapper(cls):
            doc = kwargs.pop('doc', None)
            if doc is not None:
                self._handle_api_doc(cls, doc)

            if getattr(cls,'_path', None) is None:
                cls._path = url
            else:
                if cls._path != url:
                    raise ValueError

            self.add_resource(cls, url, **kwargs)
            return cls
        return wrapper

    def _handle_api_doc(self, cls, doc):
        """Adds __apidoc__ to a given class with adapted doc dictionary content"""

        if doc is False:
            cls.__apidoc__ = False
            return
        unshortcut_params_description(doc)
        handle_deprecations(doc)
        if isclass(cls):
            for http_method in [method.lower() for method in get_resource_http_methods(cls)]:
                if http_method in doc:
                    if doc[http_method] is False:
                        continue
                    unshortcut_params_description(doc[http_method])
                    handle_deprecations(doc[http_method])
                    if 'expect' in doc[http_method] and not isinstance(doc[http_method]['expect'], (list, tuple)):
                        doc[http_method]['expect'] = [doc[http_method]['expect']]
        cls.__apidoc__ = merge(getattr(cls, '__apidoc__', {}), doc)

    def doc(self, shortcut=None, **kwargs):
        """A decorator to add some api documentation to the decorated object"""

        if isinstance(shortcut, six.text_type):
            kwargs['id'] = shortcut

        show = shortcut if isinstance(shortcut, bool) else True

        def wrapper(documented):
            self._handle_api_doc(documented, kwargs if show else False)
            return documented
        return wrapper


    def hide(self, func):
        """A decorator to hide a resource or a method from specifications"""
        return self.doc(False)(func)


    def add_model(self, name, definition):
        self.models[name] = definition
        for api in self.apis:
            api.models[name] = definition
        return definition

    def model(self, name=None, model=None, mask=None, **kwargs):
        """
        Register a model

        .. seealso:: :class:`Model`
        """
        model = Model(name, model, mask=mask)
        model.__apidoc__.update(kwargs)
        return self.add_model(name, model)

    def extend(self, name, parent, fields):
        """
        Extend a model (Duplicate all fields)

        :deprecated: since 0.9. Use :meth:`clone` instead
        """
        if isinstance(parent, list):
            parents = parent + [fields]
            model = Model.extend(name, *parents)
        else:
            model = Model.extend(name, parent, fields)
        return self.add_model(name, model)

    def clone(self, name, *specs):
        """
        Clone a model (Duplicate all fields)

        :param str name: the resulting model name
        :param specs: a list of models from which to clone the fields

        .. seealso:: :meth:`Model.clone`

        """
        model = Model.clone(name, *specs)
        return self.add_model(name, model)

    def inherit(self, name, *specs):
        """
        Inherit a modal (use the Swagger composition pattern aka. allOf)

        .. seealso:: :meth:`Model.inherit`
        """
        model = Model.inherit(name, *specs)
        return self.add_model(name, model)

    def expect(self, *inputs, **kwargs):
        """
        A decorator to Specify the expected input model

        :param Model|Parse inputs: An expect model or request parser
        :param bool validate: whether to perform validation or not

        """
        expect = []
        params = {
            'validate': kwargs.get('validate', None) or self._validate,
            'expect': expect
        }
        for param in inputs:
            expect.append(param)
        return self.doc(**params)


    def payload_model(self, *models):
        """A decorator that adds payload parameters model data to swagger api documentation as well as
        applies wsgiservice validation using the model object provided.

        :param models: model(s) objects to extract api information from on request payload model
        """

        expect = []
        params = {
            'validate': self._validate,
            'expect': expect
        }
        validations = {}

        for model in models:
            expect.append(model)
            model_validations = self._prepare_validation_dict(model)
            validations.update(model_validations)

        def wrapper(documented):

            if not hasattr(documented, '_validations'):
                documented._validations = {}
            documented._validations.update(validations)

            self._handle_api_doc(documented, params)
            return documented

        return wrapper

    def _prepare_validation_dict(self, model):
        """Generates the content of the _validations dictionary (normally used by validate decorator \
        from wsgiservice.decorators) from a single Model object.

        :param model: instance of the
        :return: validations dictionary (equivalent to _validations from validate decorator from wsgiservice)
        :rtype: dict
        """

        validations = {}

        for field_name, field in six.iteritems(model):
            validations[field_name] = {
                're': field.valid_params.get('re', None),
                'convert': field.valid_params.get('convert', None),
                'doc': field.valid_params.get('doc', None),
                'mandatory': field.valid_params.get('mandatory', False),
            }

        return validations

    def as_list(self, field):
        """Allow to specify nested lists for documentation"""
        field.__apidoc__ = merge(getattr(field, '__apidoc__', {}), {'as_list': True})
        return field


    def marshal_with(self, fields, as_list=False, code=200, description=None, **kwargs):
        """
        A decorator to specify the returned response object values: attaches __apidoc__ attribute
        to the decorated class or method.

        :param bool as_list: Indicate that the return type is a list (for the documentation)
        :param int code: Optionally give the expected HTTP response code if its different from 200
        """

        def wrapper(func):
            doc = {
                'responses': {
                    code: (description, [fields]) if as_list else (description, fields)
                },
            }
            func.__apidoc__ = merge(getattr(func, '__apidoc__', {}), doc)
            return func

        return wrapper


    def marshal_list_with(self, fields, **kwargs):
        """A shortcut decorator for :meth:`~Api.marshal_with` with ``as_list=True``"""
        return self.marshal_with(fields, True, **kwargs)


    def errorhandler(self, exception):
        """A decorator to register an error handler for a given exception"""
        if inspect.isclass(exception) and issubclass(exception, Exception):
            # Register an error handler for a given exception
            def wrapper(func):
                self.error_handlers[exception] = func
                return func
            return wrapper
        else:
            # Register the default error handler
            self.default_error_handler = exception
            return exception


    def param(self, name, description=None, _in='query', **kwargs):
        """
        A decorator to specify one of the expected parameters

        :param str name: the parameter name
        :param str description: a small description of the parameter
        :param str _in: the parameter location `(query|header|path|formData|body|cookie)`, by default set to `query`
        """
        param = kwargs
        param['in'] = _in
        param['description'] = description
        return self.doc(params={name: param})


    def valid_param(self, name, doc='', _in='query', re=None, convert=None, mandatory=True, **kwargs):
        """
        A decorator to specify one of the expected parameters and append validation conditions \
        for wsgiservice. This is a hybryd decorator made from self.param, self.doc and \
        wsgiservice.decorators.validate().

        :param str name: the parameter name
        :param str doc: Parameter description for the API documentation.
        :param str _in: the parameter location `(query|header|path|formData|body|cookie)`, `query` by default.
        :param re: Regular expression to search for in the input parameter. If
               this is not set, just validates if the parameter has been set.
        :type re: regular expression
        :param convert: Callable to convert the validated parameter value to the
                    final data type. Ideal candidates for this are the
                    built-ins int or float functions. If the function raises a
                    ValueError, this is reported to the client as a 400 error.
        :type convert: callable or type (eg. int, str, bool, etc.)
        :param mandatory: Whether the parameter is mandatory. By default this is `True`.
        :type mandatory: bool
        """

        param = kwargs
        param['required'] = mandatory
        param['in'] = _in
        param['description'] = doc or None

        if type(convert) == type:
            param['type'] = convert
        elif hasattr(convert, "converts_to_type"):
            param['type'] = eval(convert.converts_to_type)

        api_params = {'params': {name: param}}

        def wrapper(documented):

            if not hasattr(documented, '_validations'):
                documented._validations = {}
            documented._validations[name] = {'re': re, 'convert': convert, 'doc': doc, 'mandatory': mandatory}

            self._handle_api_doc(documented, api_params)
            return documented

        return wrapper


    def path_param(self, name, doc=None, re=None, convert=None, mandatory=True, **kwargs):
        """Validates and annotates the path parameter."""

        return self.valid_param(name, doc=doc, _in='path', re=re,
                                convert=convert, mandatory=mandatory, **kwargs)

    def query_param(self, name, doc=None, re=None, convert=None, mandatory=True, **kwargs):
        """Validates and annotates a query parameter."""

        return self.valid_param(name, doc=doc, _in='query', re=re,
                                convert=convert, mandatory=mandatory, **kwargs)

    def payload_param(self, name, doc=None, re=None, convert=None, mandatory=True, **kwargs):
        """Validates and annotates a parameter given in a payload body."""

        return self.valid_param(name, doc=doc, _in='body', re=re,
                                convert=convert, mandatory=mandatory, **kwargs)


    def response(self, code, description, model=None, **kwargs):
        """
        A decorator to specify one of the expected responses

        :param int code: the HTTP status code
        :param str description: a small description about the response
        :param Model model: an optional response model

        """
        return self.doc(responses={code: (description, model) if model else description})


    def header(self, name, description=None, **kwargs):
        """
        A decorator to specify one of the expected headers

        :param str name: the HTTP header name
        :param str description: a description about the header

        """
        return self.param(name, description=description, _in='header', **kwargs)


    def deprecated(self, func):
        """A decorator to mark a resource or a method as deprecated"""
        return self.doc(deprecated=True)(func)


    def security(self, *security_definition_names):
        """
        Operation security decorator

        Positional arguments specify alternative security requirements to use the operation.
        Requirements validity check is done when adding namespace to Api
        """

        def wrapper(documented):
            return self.doc(security=security_definition_names)(documented)
        return wrapper


def unshortcut_params_description(data):
    if 'params' in data:
        for name, description in six.iteritems(data['params']):
            if isinstance(description, six.string_types):
                data['params'][name] = {'description': description}


def handle_deprecations(doc):
    if 'parser' in doc:
        warnings.warn('The parser attribute is deprecated, use expect instead', DeprecationWarning, stacklevel=2)
        doc['expect'] = doc.get('expect', []) + [doc.pop('parser')]
    if 'body' in doc:
        warnings.warn('The body attribute is deprecated, use expect instead', DeprecationWarning, stacklevel=2)
        doc['expect'] = doc.get('expect', []) + [doc.pop('body')]
