from paste.deploy.converters import asbool
from dateutil.parser import parse as parse_datetime


def Boolean(value):
    """Converts value to Boolean"""
    return asbool(value)

def String(value):
    """Converts value to a string"""
    return value

def Integer(value):
    """Converts value to Integer"""
    return int(value)

def DateTime(value):
    """Converts value to a valid datetime"""
    return parse_datetime(value)

