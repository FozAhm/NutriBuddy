# ======================================================
# ======================================================
# LOCATIONS
# ======================================================
# ======================================================

from flask_restplus import Namespace, Resource, fields, reqparse
from flask import render_template, request

import uuid
from functools import reduce  # forward compatibility for Python 3
import requests, json
import datetime
from neo4j.v1 import GraphDatabase, basic_auth

from nodes.constants import username, password, neo_http_ap, neo_bolt_ap, node_labels, relationship_types, list_queries
from nodes.SimpleLogger.SimpleLogger import SimpleLogger
from nodes.queries import *

#======================================

logger = SimpleLogger('LocationsManager', 5)

# orchestrator= os.getenv('Orchestrator_AP' ,'0.0.0.0:5000')
# mongoIP=os.getenv('CMDB_AP' ,'0.0.0.0:27017')
# client = MongoClient(mongoIP.split(":")[0], int(mongoIP.split(":")[1]) , connect=False)
# #client = MongoClient("mongodb://mongodb0.example.net:27017")
# db = client.client

api = Namespace('locations', description='Neo4j location-related operations')

locations = api.model('locations', {
    'type': fields.String(description='The resource identifier'),
})

locations_container = api.model('locationsContainer', {
    'locations': fields.Nested(locations),
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
    create_argparser.add_argument('name', type=str, required=True, location='form', help='Location name')
    create_argparser.add_argument('beacon_id', type=str, required=False, location='form', help='Location name')
    create_argparser.add_argument('address', type=str, required=False, location='form', help='Location name')
    # TODO: Allow other properties
    @api.expect(create_argparser)
    @api.doc(responses={
        200: 'Success',
        400: 'Validation Error'
    })
    def post(self, name=None):
        '''Add a location'''
        try:
            args = create_argparser.parse_args()
            if args['name']:
                name = args['name']
            else:
                return '`name` is a required field', 400
            if args['beacon_id']:
                beacon_id = args['beacon_id']
            else:
                beacon_id = 'null'
            if args['address']:
                address = args['address']
            else:
                address ='null'
            label = 'Location'
            # Create new node
            url = neo_http_ap + '/db/data/node'
            data = {
                    'name': name,
                    'uuid': str(uuid.uuid4()),
                    'beacon_id': beacon_id,
                    'address' : address
                    }
            data = json.dumps(data, separators=(',',':'))
            response = session.post(url, data=data, headers=headers, verify=False)
            if (response.ok):
                logger.debug('Successfully created location: ' + str(response))
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
            jsondata = json.loads(response.content)
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


read_argparser = argparser.copy()
@api.route('/<string:target_uuid>/get')
class Read(Resource):
    @api.expect(read_argparser)
    @api.doc(responses={
        200: 'Success',
        400: 'Validation Error'
    })
    def get(self, target_uuid):
        '''Get a location by UUID'''
        try:
            args = read_argparser.parse_args()
            url = neo_http_ap + '/db/data/cypher'
            try:
                data = {'query': get_location_id_by_uuid, 'params': {'uuid': str(target_uuid)}}
                data = json.dumps(data, separators=(',', ':'))
                response = session.post(url, data=data, verify=False)
                if (response.ok):
                    target_id = response.json()['data'][0][0]  # Response gives what should be an int as a double array, needs to be 0 indexed twice to isolate
            except:
                message = 'Location could not be found\n'
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
                message = 'Response to location retrieval not OK:\n%s' % response_dump
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
        '''Get 1000 locations'''
        try:
            url = neo_http_ap + '/db/data/label/Location/nodes'
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
                message = 'Response to communities retrieval was not OK:\n%s' % response_dump
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
        '''Update location node, empty value will delete property'''
        try:
            args = update_argparser.parse_args()
            if args['property']:
                property = args['property']
            else:
                return '`property` is a required field', 400
            url = neo_http_ap + '/db/data/cypher'
            try:
                data = {'query': get_location_id_by_uuid, 'params': {'uuid': str(target_uuid)}}
                data = json.dumps(data, separators=(',', ':'))
                response = session.post(url, data=data, verify=False)
                if (response.ok):
                    target_id = response.json()['data'][0][0]  # Response gives what should be an int as a double array, needs to be 0 indexed twice to isolate
            except:
                message = 'Location could not be found\n'
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
                message = 'Response to location properties retrieval not OK:\n%s' % response_dump
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
                    return {'message': 'Location successfully updated', 'response': str(response)}, 200
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
        '''Delete a location by UUID'''
        try:
            url = neo_http_ap + '/db/data/cypher'
            try:
                data = {'query': get_location_id_by_uuid, 'params': {'uuid': str(target_uuid)}}
                data = json.dumps(data, separators=(',', ':'))
                response = session.post(url, data=data, verify=False)
                if (response.ok):
                    target_id = response.json()['data'][0][0]  # Response gives what should be an int as a double array, needs to be 0 indexed twice to isolate
            except:
                message = 'Location could not be found\n'
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
                return {'message': 'Location deletion was successful', 'response': str(response)}, 200
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

get_org_argparser = argparser.copy()
@api.route('/<string:target_uuid>/getorganization')
class Get(Resource):
    @api.expect(get_org_argparser)
    @api.doc(responses={
        200: 'Success',
        400: 'Validation Error'
    })
    def get(self, target_uuid):
        '''Delete a location by UUID'''
        try:
            url = neo_http_ap + '/db/data/cypher'
            try:
                data = {'query': get_location_org, 'params': {'uuid': str(target_uuid)}}
                data = json.dumps(data, separators=(',', ':'))
                response = session.post(url, data=data, verify=False)
                org = response.json()['data'][0][0]['data']
            except:
                message = 'Location could not be found\n'
                logger.debug(message)
                return message, 400

            return org, 200

        except Exception as exc:
            message = 'Something went wrong'
            logger.critical(message)
            logger.dump_exception(exc)
            return message, 500

#TODO: Add filtering versions of this search
get_products_argparser = argparser.copy()
@api.route('/<string:target_uuid>/getproducts')
class Get(Resource):
    @api.expect(get_products_argparser)
    @api.doc(responses={
        200: 'Success',
        400: 'Validation Error'
    })
    def get(self, target_uuid):
        '''get All offered products'''
        try:
            url = neo_http_ap + '/db/data/cypher'
            try:
                data = {'query': get_location_products, 'params': {'uuid': str(target_uuid)}}
                data = json.dumps(data, separators=(',', ':'))
                response = session.post(url, data=data, verify=False)
                products = response.json()['data']
            except:
                message = 'Relationship could not be found\n'
                logger.debug(message)
                return message, 400

            return_list = []
            for product in products:
                return_list.append(product[0]['data'])
            return return_list

        except Exception as exc:
            message = 'Something went wrong'
            logger.critical(message)
            logger.dump_exception(exc)
            return message, 500

toggleflyer_argparser = argparser.copy()
@api.route('/<string:target_uuid>/toggleflyer')
class Put(Resource):
    toggleflyer_argparser.add_argument('product_uuid', type=str, required=True, location='form', help='Product to toggle on/off the flyer')
    @api.expect(toggleflyer_argparser)
    @api.doc(responses={
        200: 'Success',
        400: 'Validation Error'
    })
    def put(self, target_uuid):
        '''Put or remove a target from the flyer'''
        try:
            args = toggleflyer_argparser.parse_args()
            if args['product_uuid']:
                product_uuid = args['product_uuid']
            else:
                return '`product_uuid` is a required field', 400

            url = neo_http_ap + '/db/data/cypher'
            try:
                data = {'query': get_available_at, 'params': {'uuid2': str(target_uuid), 'uuid1': product_uuid}}
                data = json.dumps(data, separators=(',', ':'))
                response = session.post(url, data=data, verify=False)
                relationship_id = response.json()['data'][0][0]
            except:
                message = 'Relationship could not be found\n'
                logger.debug(message)
                return message, 400

            url = neo_http_ap + '/db/data/relationship/' + str(relationship_id) + '/properties'
            response = session.get(url, verify=False)
            if not (response.ok):
                response_dump = None
                try:
                    response_dump = response.json()
                except:
                    response_dump = logger.dump_var(response)
                message = 'Response to available_at properties retrieval not OK:\n%s' % response_dump
                logger.debug(message)
                return message, 400
            rel_content = response.json()
            if rel_content['on_flyer'] == 'False':
                rel_content['on_flyer'] = 'True'
            else:
                rel_content['on_flyer'] = 'False'

            data = json.dumps(rel_content, separators=(',', ':'))
            response = session.put(url, data=data, verify=False)
            if (response.ok):
                return {'message': 'Relationship property toggled', 'response': str(response)}, 200
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

@api.route('/<string:target_uuid>/getflyer')
class Get(Resource):
    @api.expect()
    @api.doc(responses={
        200: 'Success',
        400: 'Validation Error'
    })
    def get(self, target_uuid):
        '''Get a location's flyer flyer'''
        try:

            url = neo_http_ap + '/db/data/cypher'
            try:
                data = {'query': get_flyer, 'params': {'uuid': str(target_uuid)}}
                data = json.dumps(data, separators=(',', ':'))
                response = session.post(url, data=data, verify=False)
                products = response.json()['data']
            except:
                message = 'Relationship could not be found\n'
                logger.debug(message)
                return message, 400

            responses = []
            for product in products:
                responses.append(product[0]['data'])

            return responses, 200

        except Exception as exc:
            message = 'Something went wrong'
            logger.critical(message)
            logger.dump_exception(exc)
            return message, 500