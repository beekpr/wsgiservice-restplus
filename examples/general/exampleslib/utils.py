# The non-persistent document data store
data = {}


def update_document(id, doc_resource_request_post):
    """Overwrite or create the document indicated by the ID.
    Parameters are passed as key/value pairs in the POST data.
    """

    data.setdefault(id, {'id': id})
    for key in doc_resource_request_post:
        data[id][key] = doc_resource_request_post[key]

    return {'id': id, 'saved': True}


def put_document(id, doc_resource_request_post):
    """Overwrite or create the document indicated by the ID. Parameters
    are passed as key/value pairs in the POST data."""

    data.setdefault(id, {'id': id})
    for key in doc_resource_request_post:
        data[id][key] = doc_resource_request_post[key]

    return {'id': id, 'saved': True}


def token_authentication(request):
    if request.header.get('Authorization', None) and request.header['Authorization'][:5].lower() == 'token':
        return request.header['Authorization'][5:].strip(' ') == 'secret_1234'
    else:
        return False
