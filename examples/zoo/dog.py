from wsgiservice import Resource, raise_404

from wsgiservice_restplus import fields
from wsgiservice_restplus.namespace import Namespace

ns = Namespace('dogs', description='Dogs related operations')

dog_model = ns.model('Dog', {
    'id': fields.String(required=True, description='The dog identifier'),
    'name': fields.String(required=True, description='The dog name'),
})

DOGS = [
    {'id': 'medor', 'name': 'Medor'},
]


@ns.route('/')
class DogList(Resource):
    @ns.doc('list_dogs')
    @ns.marshal_list_with(dog_model)
    def GET(self):
        '''List all dogs'''
        return DOGS


@ns.route('/{id}')
@ns.param('id', 'The dog identifier')
@ns.response(404, 'Dog not found')
class Dog(Resource):
    @ns.doc('get_dog')
    @ns.marshal_with(dog_model)
    def GET(self, id):
        '''Fetch a dog given its identifier'''
        for dog in DOGS:
            if dog['id'] == id:
                return dog
        raise_404