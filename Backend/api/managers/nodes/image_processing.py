# ======================================================
# ======================================================
# PRODUCTS
# ======================================================
# ======================================================

from flask_restplus import Namespace, Resource, fields, reqparse
from flask import render_template, request, send_file

import uuid
from functools import reduce  # forward compatibility for Python 3
import requests, json

from neo4j.v1 import GraphDatabase, basic_auth

from nodes.constants import username, password, neo_http_ap, neo_bolt_ap, node_labels, relationship_types, list_queries
from nodes.SimpleLogger.SimpleLogger import SimpleLogger
from nodes.queries import *

#======================================

logger = SimpleLogger('ProductsManager', 5)

# orchestrator= os.getenv('Orchestrator_AP' ,'0.0.0.0:5000')
# mongoIP=os.getenv('CMDB_AP' ,'0.0.0.0:27017')
# client = MongoClient(mongoIP.split(":")[0], int(mongoIP.split(":")[1]) , connect=False)
# #client = MongoClient("mongodb://mongodb0.example.net:27017")
# db = client.client

api = Namespace('image processing', description='to get and return')

products = api.model('products', {
    'type': fields.String(description='The resource identifier'),
})

products_container = api.model('productsContainer', {
    'products': fields.Nested(products),
})

session = requests.Session()
headers = {'Content-Type': 'multipart/form-data', 'Accept': 'application/json'}
session.auth = (username, password)

argparser = reqparse.RequestParser()


# ======================================================
# CLASSES
# ======================================================

create_argparser = argparser.copy()
@api.route('/add')
class Create(Resource):
    create_argparser.add_argument('UPC', type=str, required=True, location='form', help='Product UPC')
    create_argparser.add_argument('name', type=str, required=True, location='form', help='Product name')
    create_argparser.add_argument('description', type=str, required=False, location='form', help='Product description')
    create_argparser.add_argument('image_name', type=str, required=False, location='form', help='Image file name')
    # TODO: Allow other properties
    @api.expect(create_argparser)
    @api.doc(responses={
        200: 'Success',
        400: 'Validation Error'
    })
    def post(self):
        '''Add a product'''
        try:
            args = create_argparser.parse_args()
            if args['UPC']:
                UPC = args['UPC']
            else:
                return '`UPC` is a required field', 400
            if args['name']:
                name = args['name']
            else:
                return '`name` is a required field', 400
            if args['image_name']:
                image = args['image_name']
            else:
                image = 'null'
            if args['description']:
                description = args['description']
            else:
                description = 'null'
            label = 'Product'
            # Create new node
            url = neo_http_ap + '/db/data/node'
            data = {
                    'uuid': str(uuid.uuid4()),
                    'UPC': UPC,
                    'name': name,
                    'description': description,
                    'image': image
                    }
            data = json.dumps(data, separators=(',',':'))
            response = session.post(url, data=data, headers=headers, verify=False)
            if (response.ok):
                logger.debug('Successfully created product: ' + str(response))
            else:
                response_dump = None
                try:
                    response_dump = response.json()
                except:
                    response_dump = logger.dump_var(response)
                message = 'Response to node addition not OK:\n%s' % response_dump
                logger.debug(message)
                return message, 400
            # Label newly-created node
            jsondata = json.loads(str(response.content, 'utf-8'))
            new_node_id = jsondata['metadata']['id']
            url = neo_http_ap + '/db/data/node/' + str(new_node_id) + '/labels'
            data = [label]
            data = json.dumps(data, separators=(',',':'))
            logger.debug('Data to send: ' + data)
            response = session.post(url, data=data, headers=headers, verify=False)
            if (response.ok):
                return {'message': 'Node addition successful', 'response': str(response)}, 200
            else:
                response_dump = None
                try:
                    response_dump = response.json()
                except:
                    response_dump = logger.dump_var(response)
                message = 'Response to label addition not okay:\n%s' % response_dump
                logger.debug(message)
                return message, 400
        except Exception as exc:
            message = 'Something went wrong'
            logger.critical(message)
            logger.dump_exception(exc)
            return message, 500

#Get by UUID
read_argparser = argparser.copy()
@api.route('/<string:target_uuid>/get')
class Read(Resource):
    @api.expect(read_argparser)
    @api.doc(responses={
        200: 'Success',
        400: 'Validation Error'
    })
    def get(self, target_uuid):
        '''Get a product by UUID'''
        try:
            args = read_argparser.parse_args()
            url = neo_http_ap + '/db/data/cypher'
            try:
                data = {'query': get_product_id_by_uuid, 'params': {'uuid': str(target_uuid)}}
                data = json.dumps(data, separators=(',', ':'))
                response = session.post(url, data=data, verify=False)
                if (response.ok):
                    target_id = response.json()['data'][0][0]  # Response gives what should be an int as a double array, needs to be 0 indexed twice to isolate
            except:
                message = 'Product could not be found\n'
                logger.debug(message)
                return message, 400
            url = neo_http_ap + '/db/data/node/' + str(target_id) + '/properties'
            response = session.get(url, verify=False)
            if (response.ok):
                return response.json(), 200
            else:
                response_dump = None
                try:
                    response_dump = response.json()
                except:
                    response_dump = logger.dump_var(response)
                message = 'Response to product retrieval not OK:\n%s' % response_dump
                logger.debug(message)
                return message, 400
        except Exception as exc:
            message = 'Something went wrong'
            logger.critical(message)
            logger.dump_exception(exc)
            return message, 500

#Get by UPC
read_argparser = argparser.copy()
@api.route('/<string:target_UPC>/getbyUPC')
class Read(Resource):
    @api.expect(read_argparser)
    @api.doc(responses={
        200: 'Success',
        400: 'Validation Error'
    })
    def get(self, target_UPC):
        '''Get a product by UPC'''
        try:
            args = read_argparser.parse_args()
            url = neo_http_ap + '/db/data/cypher'
            try:
                data = {'query': get_product_id_by_UPC, 'params': {'UPC': str(target_UPC)}}
                data = json.dumps(data, separators=(',', ':'))
                response = session.post(url, data=data, verify=False)
                print(response.json())
                if (response.ok):
                    target_id = response.json()['data'][0][0]  # Response gives what should be an int as a double array, needs to be 0 indexed twice to isolate
            except:
                message = 'Product could not be found\n'
                logger.debug(message)
                return message, 400
            url = neo_http_ap + '/db/data/node/' + str(target_id) + '/properties'
            response = session.get(url, verify=False)
            if (response.ok):
                return response.json(), 200
            else:
                response_dump = None
                try:
                    response_dump = response.json()
                except:
                    response_dump = logger.dump_var(response)
                message = 'Response to product retrieval not OK:\n%s' % response_dump
                logger.debug(message)
                return message, 400
        except Exception as exc:
            message = 'Something went wrong'
            logger.critical(message)
            logger.dump_exception(exc)
            return message, 500

readmany_argparser = argparser.copy()
@api.route('/getmany')
class ReadMany(Resource):
    @api.expect(readmany_argparser)
    @api.doc(responses={
        200: 'Success',
        400: 'Validation Error'
    })
    def get(self):
        '''Get 1000 products'''
        try:
            url = neo_http_ap + '/db/data/label/Product/nodes'
            response = session.get(url, verify=False)
            if (response.ok):
                nodes = []
                for node in response.json():
                    nodes.append(node['data'])
                return nodes, 200
            else:
                response_dump = None
                try:
                    response_dump = response.json()
                except:
                    response_dump = logger.dump_var(response)
                message = 'Response to products retrieval was not OK:\n%s' % response_dump
                logger.debug(message)
                return message, 400
        except Exception as exc:
            message = 'Something went wrong'
            logger.critical(message)
            logger.dump_exception(exc)
            return message, 500

update_argparser = argparser.copy()
@api.route('/<string:target_uuid>/update')
class Update(Resource):
    update_argparser.add_argument('property', type=str, required=True, location='form', help='Field to be updated')
    update_argparser.add_argument('value', type=str, required=False, location='form',help='Desired value of field')
    @api.expect(update_argparser)
    @api.doc(responses={
        200: 'Success',
        400: 'Validation Error'
    })
    def put(self, target_uuid, property = None, value = None):
        '''Update product node, empty value will delete property'''
        try:
            args = update_argparser.parse_args()
            if args['property']:
                property = args['property']
            else:
                return '`property` is a required field', 400
            url = neo_http_ap + '/db/data/cypher'
            try:
                data = {'query': get_product_id_by_uuid, 'params': {'uuid': str(target_uuid)}}
                data = json.dumps(data, separators=(',', ':'))
                response = session.post(url, data=data, verify=False)
                if (response.ok):
                    target_id = response.json()['data'][0][0]
            except:
                message = 'Product could not be found\n'
                logger.debug(message)
                return message, 400

            url = neo_http_ap + '/db/data/node/' + str(target_id) + '/properties'
            response = session.get(url, verify = False)
            if not (response.ok):
                response_dump = None
                try:
                    response_dump = response.json()
                except:
                    response_dump = logger.dump_var(response)
                message = 'Response to product properties retrieval not OK:\n%s' % response_dump
                logger.debug(message)
                return message, 400
            node_content = response.json()
            if args['value']:
                value = args['value']
                node_content[property] = value
            else:
                node_content[property] = 'null'

            data = json.dumps(node_content, separators=(',', ':'))
            response = session.put(url, data=data, verify=False)
            if (response.ok):
                    return {'message': 'Product successfully updated', 'response': str(response)}, 200
            else:
                response_dump = None
                try:
                    response_dump = response.json()
                except:
                    response_dump = logger.dump_var(response)
                message = 'Response to update was not OK:\n%s' % response_dump
                logger.debug(message)
                return message, 400

        except Exception as exc:
            message = 'Something went wrong'
            logger.critical(message)
            logger.dump_exception(exc)
            return message, 500

delete_argparser = argparser.copy()
@api.route('/<string:target_uuid>/remove')
class Delete(Resource):
    @api.expect(delete_argparser)
    @api.doc(responses={
        200: 'Success',
        400: 'Validation Error'
    })
    def delete(self, target_uuid):
        '''Delete a product by UUID'''
        try:
            url = neo_http_ap + '/db/data/cypher'
            try:
                data = {'query': get_product_id_by_uuid, 'params': {'uuid': str(target_uuid)}}
                data = json.dumps(data, separators=(',', ':'))
                response = session.post(url, data=data, verify=False)
                if (response.ok):
                    target_id = response.json()['data'][0][0]  # Response gives what should be an int as a double array, needs to be 0 indexed twice to isolate
            except:
                message = 'Product could not be found\n'
                logger.debug(message)
                return message, 400
            # Get and delete all relationships of node first
            url = neo_http_ap + '/db/data/node/' + str(target_id) + '/relationships/all'
            response = session.get(url, verify=False)
            if (response.ok):
                for node in response.json():
                    url = neo_http_ap + '/db/data/relationship/' + str(node['metadata']['id'])
                    response = session.delete(url, verify=False)
                    if (not response.ok):
                        try:
                            problem = response.json()
                        except:
                            problem = response
                        return ('Response to relationship deletion not OK: %s' % str(problem)), 400
            else:
                response_dump = None
                try:
                    response_dump = response.json()
                except:
                    response_dump = logger.dump_var(response)
                message = 'Response to GET on relationships was not OK:\n%s' % response_dump
                logger.debug(message)
                return message, 400
            args = delete_argparser.parse_args()
            # Delete node
            url = neo_http_ap + '/db/data/node/' + str(target_id)
            response = session.delete(url, verify=False)
            if (response.ok):
                return {'message': 'Product deletion was successful', 'response': str(response)}, 200
            else:
                response_dump = None
                try:
                    response_dump = response.json()
                except:
                    response_dump = logger.dump_var(response)
                message = 'Response to DELETE node was not OK:\n%s' % response_dump
                logger.debug(message)
                return message, 400
        except Exception as exc:
            message = 'Something went wrong'
            logger.critical(message)
            logger.dump_exception(exc)
            return message, 500

addlocation_argparser = argparser.copy()
@api.route('/<string:product_uuid>/add_availability')
class AddLocation(Resource):
    addlocation_argparser.add_argument('location_uuid', type=str, required=True, location='form', help='Location node ID')
    addlocation_argparser.add_argument('stock', type=str, required=False, location='form', help='Location stock of product')
    addlocation_argparser.add_argument('price', type=str, required=True, location='form', help='Product price')
    addlocation_argparser.add_argument('beacon_id', type=str, required=False, location='form', help='ID of beacon')
    @api.expect(addlocation_argparser)
    @api.doc(responses={
        200: 'Success',
        400: 'Validation Error'
    })
    def put(self, product_uuid=None, location_uuid=None, stock=None, amount=None, price=None, description=None):
        '''Product available at location and information about the product'''
        try:
            args = addlocation_argparser.parse_args()
            if args['location_uuid']:
                location_uuid = args['location_uuid']
            else:
                return '`location_uuid` is a required field', 400
            if args['price']:
                price = args['price']
            else:
                '`price` is a required field', 400
            # Searching by uuid
            url = neo_http_ap + '/db/data/cypher'
            try:
                data = {'query': get_product_id_by_uuid,
                        'params': {'uuid': str(product_uuid)}}
                data = json.dumps(data, separators=(',', ':'))
                response = session.post(url, data=data, verify=False)
                if (response.ok):
                    product_id = response.json()['data'][0][0]  # Response gives what should be an int as a double array, needs to be 0 indexed twice to isolate
            except:
                message = 'Product could not be found\n'
                logger.debug(message)
                return message, 400
            try:
                data = {'query': get_location_id_by_uuid, 'params': {'uuid': str(location_uuid)}}
                data = json.dumps(data, separators=(',', ':'))
                response = session.post(url, data=data, verify=False)
                if (response.ok):
                    location_id = response.json()['data'][0][0]  # Response gives what should be an int as a double array, needs to be 0 indexed twice to isolate
            except:
                message = 'Location could not be found\n'
                return message, 400
            relationship_type = 'available_at'
            # Create new relationship
            url = neo_http_ap + '/db/data/node/' + str(product_id) + '/relationships'
            data = {'to': neo_bolt_ap + '/db/data/node/' + str(location_id), 'type': relationship_type}
            if args['stock']:
                stock = args['stock']
            else:
                stock = "null"
            if args['beacon_id']:
                beacon_id = args['beacon_id']
            else:
                beacon_id = "null"
            data['data'] = {
                            'stock': stock,
                            'base_price': price,
                            'price_multiplier': '1.0',
                            'beacon_id': beacon_id
                            }

            data = json.dumps(data, separators=(',',':'))
            response = session.post(url, data=data, headers=headers, verify=False)
            if (response.ok):
                    return {'message': 'Product availability successfully added at location', 'response': str(response)}, 200
            else:
                response_dump = None
                try:
                    response_dump = response.json()
                except:
                    response_dump = logger.dump_var(response)
                message = 'Response to POST was not OK:\n%s' % response_dump
                logger.debug(message)
                return message, 400
        except Exception as exc:
            message = 'Something went wrong'
            logger.critical(message)
            logger.dump_exception(exc)
            return message, 500

readdetails_argparser = argparser.copy()
@api.route('/<string:product_uuid>/<string:location_uuid>/get_availability')
class Read(Resource):
    @api.expect(readdetails_argparser)
    @api.doc(responses={
        200: 'Success',
        400: 'Validation Error'
    })
    def get(self, product_uuid, location_uuid):
        '''Get a product details'''
        try:
            url = neo_http_ap + '/db/data/cypher'
            try:
                data = {'query': get_product_details, 'params': {'uuidp': str(product_uuid), 'uuidl': str(location_uuid)}}
                data = json.dumps(data, separators=(',', ':'))
                response = session.post(url, data=data, verify=False)
                if (response.ok):
                    rel = response.json()['data'][0][0]['data']
                    return rel
            except:
                message = 'Relationship could not be found\n'
                logger.debug(message)
                return message, 400

        except Exception as exc:
            message = 'Something went wrong'
            logger.critical(message)
            logger.dump_exception(exc)
            return message, 500

updatelocation_argparser = argparser.copy()
@api.route('/<string:product_uuid>/update_availability')
class Update_Location(Resource):
    updatelocation_argparser.add_argument('location_uuid', type=str, required=True, location='form',help='Location node ID')
    updatelocation_argparser.add_argument('property', type=str, required=True, location='form', help='Field to be updated')
    updatelocation_argparser.add_argument('value', type=str, required=False, location='form',help='Desired value of field')
    @api.expect(updatelocation_argparser)
    @api.doc(responses={
        200: 'Success',
        400: 'Validation Error'
    })
    def put(self, product_uuid=None, location_uuid=None):
        '''Update item availability details at location'''
        try:
            args = updatelocation_argparser.parse_args()
            if args['location_uuid']:
                location_uuid = args['location_uuid']
            else:
                return '`location_uuid` is a required field', 400
            if args['property']:
                property = args['property']
            else:
                return '`property` is a required field', 400
            url = neo_http_ap + '/db/data/cypher'
            try:
                data = {'query': get_available_at,'params': {'uuid1': str(product_uuid), 'uuid2': str(location_uuid)}}
                data = json.dumps(data, separators=(',', ':'))
                response = session.post(url, data=data, verify=False)
                if (response.ok):
                    rel_id = response.json()['data'][0][0]
            except:
                message = 'Relationship could not be found\n'
                logger.debug(message)
                return message, 400

            url = neo_http_ap + '/db/data/relationship/' + str(rel_id) + '/properties'
            response = session.get(url, verify=False)
            if not (response.ok):
                response_dump = None
                try:
                    response_dump = response.json()
                except:
                    response_dump = logger.dump_var(response)
                message = 'Response to product properties retrieval not OK:\n%s' % response_dump
                logger.debug(message)
                return message, 400
            node_content = response.json()
            if args['value']:
                value = args['value']
                node_content[property] = value
            else:
                del node_content[property]  # If 'value' arg is empty, delete the property
            data = json.dumps(node_content, separators=(',', ':'))
            response = session.put(url, data=data, verify=False)
            if (not response.ok):
                try:
                    problem = response.json()
                except:
                    problem = response
                return ('Response to relationship update not OK: %s' % str(problem)), 400
            else:
                return 'Updated item availability at location', 200

        except Exception as exc:
            message = 'Something went wrong'
            logger.critical(message)
            logger.dump_exception(exc)
            return message, 500

removelocation_argparser = argparser.copy()
@api.route('/<string:product_uuid>/remove_availability')
class Remove_Location(Resource):
    removelocation_argparser.add_argument('location_uuid', type=str, required=True, location='form', help='Location node ID')
    @api.expect(removelocation_argparser)
    @api.doc(responses={
        200: 'Success',
        400: 'Validation Error'
    })
    def delete(self, product_uuid=None, location_uuid=None,):
        '''Remove item availability at location'''
        try:
            args = removelocation_argparser.parse_args()
            if args['location_uuid']:
                location_uuid = args['location_uuid']
            else:
                return '`location_uuid` is a required field', 400
            url = neo_http_ap + '/db/data/cypher'
            try:
                data = {'query': get_available_at, 'params': {'uuid1': str(product_uuid), 'uuid2':str(location_uuid)}}
                data = json.dumps(data, separators=(',', ':'))
                response = session.post(url, data=data, verify=False)
                if (response.ok):
                    rel_id = response.json()['data'][0][0]
            except:
                message = 'Relationship could not be found\n'
                logger.debug(message)
                return message, 400
            url = neo_http_ap + '/db/data/relationship/' + str(rel_id)
            response = session.delete(url, verify=False)
            if (not response.ok):
                try:
                    problem = response.json()
                except:
                    problem = response
                return ('Response to relationship deletion not OK: %s' % str(problem)), 400
            else:
                return 'Removed item availability at location', 200

        except Exception as exc:
            message = 'Something went wrong'
            logger.critical(message)
            logger.dump_exception(exc)
            return message, 500

get_image_argparser = argparser.copy()
@api.route('/<string:target_uuid>/getimageurl')
class Read(Resource):
    @api.expect(read_argparser)
    @api.doc(responses={
        200: 'Success',
        400: 'Validation Error'
    })
    def get(self, target_uuid):
        '''Return a product's Image url'''
        try:
            args = read_argparser.parse_args()
            url = neo_http_ap + '/db/data/cypher'
            try:
                data = {'query': get_product_id_by_uuid, 'params': {'uuid': str(target_uuid)}}
                data = json.dumps(data, separators=(',', ':'))
                response = session.post(url, data=data, verify=False)
                if (response.ok):
                    target_id = response.json()['data'][0][0]  # Response gives what should be an int as a double array, needs to be 0 indexed twice to isolate
            except:
                message = 'Product could not be found\n'
                logger.debug(message)
                return message, 400
            url = neo_http_ap + '/db/data/node/' + str(target_id) + '/properties/image'
            response = session.get(url, verify=False)
            if (response.ok):
                filename = response.json()
                if (filename == 'null'):
                    return 'No associated image', 404
                return str(filename) #Might have to change the direction of the slashes to reflect linux method of file referencing
            else:
                response_dump = None
                try:
                    response_dump = response.json()
                except:
                    response_dump = logger.dump_var(response)
                message = 'Response to image retrieval not OK:\n%s' % response_dump
                logger.debug(message)
                return message, 400
        except Exception as exc:
            message = 'Something went wrong'
            logger.critical(message)
            logger.dump_exception(exc)
            return message, 500

readlocations_argparser = argparser.copy()
@api.route('/<string:product_uuid>/get_locations')
class Read(Resource):
    @api.expect(readlocations_argparser)
    @api.doc(responses={
        200: 'Success',
        400: 'Validation Error'
    })
    def get(self, product_uuid):
        '''Get a locations where product is offered'''
        try:
            url = neo_http_ap + '/db/data/cypher'
            try:
                data = {'query': get_product_locations, 'params': {'uuid': str(product_uuid)}}
                data = json.dumps(data, separators=(',', ':'))
                response = session.post(url, data=data, verify=False)
                locations = response.json()['data']
            except:
                message = 'Relationship could not be found\n'
                logger.debug(message)
                return message, 400

            for location in locations:
                location = location[0]['data']
            return locations

        except Exception as exc:
            message = 'Something went wrong'
            logger.critical(message)
            logger.dump_exception(exc)
            return message, 500
