from wsgiservice import Resource, raise_404

from wsgiservice_restplus import fields
from wsgiservice_restplus.namespace import Namespace

ns = Namespace('cats', description='Cats related operations')

cat_model = ns.model('Cat', {
    'id': fields.String(required=True, description='The cat identifier'),
    'name': fields.String(required=True, description='The cat name'),
})

CATS = [
    {'id': 'felix', 'name': 'Felix'},
]


@ns.route('/')
class CatList(Resource):

    @ns.doc('list_cats')
    @ns.marshal_list_with(cat_model)
    def GET(self):
        '''List all cats'''
        return CATS


@ns.route('/<id>')
@ns.param('id', 'The cat identifier')
@ns.response(404, 'Cat not found')
class Cat(Resource):

    @ns.doc('get_cat')
    @ns.marshal_with(cat_model)
    def GET(self, id):
        '''Fetch a cat given its identifier'''
        for cat in CATS:
            if cat['id'] == id:
                return cat
        raise_404
