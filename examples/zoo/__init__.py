from wsgiservice_restplus.api import Api

from .cat import ns as cat_api
from .dog import ns as dog_api

api = Api(
    title='Zoo API',
    version='1.0',
    description='A simple demo API',
    default_mediatype='application/json',
    prefix='/',
)

api.add_namespace(cat_api)
api.add_namespace(dog_api)
