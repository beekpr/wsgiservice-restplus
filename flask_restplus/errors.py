# -*- coding: utf-8 -*-
from __future__ import unicode_literals

__all__ = (
    # 'abort',
    'RestError',
    'ValidationError',
    'SpecsError',
    'SecurityError',
)

class RestError(Exception):
    '''Base class for all wsgiservice-Restplus Errors'''
    def __init__(self, msg):
        self.msg = msg

    def __str__(self):
        return self.msg


class ValidationError(RestError):
    '''An helper class for validation errors.'''
    pass


class SpecsError(RestError):
    '''An helper class for incoherent specifications.'''
    pass

class SecurityError(RestError):
    '''Specifies inconsistency in security specificatin .'''
    pass