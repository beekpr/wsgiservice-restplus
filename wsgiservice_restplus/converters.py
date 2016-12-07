from paste.deploy.converters import asbool

def Boolean(value):
    """Converts value to Boolean"""
    return asbool(value)


def String(value):
    """Converts value to a string"""
    return value