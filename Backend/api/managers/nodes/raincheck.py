# ======================================================
# ======================================================
# Rainchecks
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


logger = SimpleLogger('RainchecksManager', 5)

# orchestrator= os.getenv('Orchestrator_AP' ,'0.0.0.0:5000')
# mongoIP=os.getenv('CMDB_AP' ,'0.0.0.0:27017')
# client = MongoClient(mongoIP.split(":")[0], int(mongoIP.split(":")[1]) , connect=False)
# #client = MongoClient("mongodb://mongodb0.example.net:27017")
# db = client.client

api = Namespace('rainchecks', description='Neo4j raincheck-related operations')

rainchecks = api.model('rainchecks', {
    'type': fields.String(description='The resource identifier'),
})

rainchecks_container = api.model('rainchecksContainer', {
    'rainchecks': fields.Nested(rainchecks),
})

session = requests.Session()
headers = {'Content-Type': 'multipart/form-data', 'Accept': 'application/json'}
session.auth = (username, password)

argparser = reqparse.RequestParser()


# ======================================================
# CLASSES
# ======================================================

# TODO: Change returns for Neo 404s
create_argparser = argparser.copy()
@api.route('/add')
class Create(Resource):
    create_argparser.add_argument('consumerUUID', type=str, required=True, location='form', help='Consumer id')
    create_argparser.add_argument('locationUUID', type=str, required=True, location='form', help='Location id')
    create_argparser.add_argument('productUUID', type=str, required=True, location='form', help='Product id')
    create_argparser.add_argument('expiryDate', type=str, required=True, location='form', help='Format yyyy-mm-dd hour:minute')
    create_argparser.add_argument('salePrice', type=str, required=True, location='form', help='Price to be given')
    # TODO: Allow other properties
    @api.expect(create_argparser)
    @api.doc(responses={
        200: 'Success',
        400: 'Validation Error'
    })
    def post(self, name=None):
        '''Add a raincheck'''
        try:
            args = create_argparser.parse_args()
            if args['consumerUUID']:
                consumer_uuid = args['consumerUUID']
            else:
                return '`consumerUUID` is a required field', 400
            if args['locationUUID']:
                location_uuid = args['locationUUID']
            else:
                return '`locationUUID` is a required field', 400
            if args['productUUID']:
                product_uuid = args['productUUID']
            else:
                return '`productUUID` is a required field', 400
            if args['expiryDate']:
                expiryDate = datetime.datetime.strptime(args['expiryDate'],"%Y-%m-%d %H:%M")
            else:
                return '`expiryDate` is a required field', 400
            if args['salePrice']:
                salePrice = args['salePrice']
            else:
                return '`salePrice` is a required field', 400

            try:
                url = neo_http_ap + '/db/data/cypher'
                data = {'query': get_consumer_id_by_uuid, 'params': {'uuid': str(consumer_uuid)}}
                data = json.dumps(data, separators=(',', ':'))
                response = session.post(url, data=data, verify=False)
                consumer_id = response.json()['data'][0][0]
            except:
                message = 'Consumer could not be found\n'
                logger.debug(message)
                return message, 400
            try:
                data = {'query': get_location_id_by_uuid, 'params': {'uuid': str(location_uuid)}}
                data = json.dumps(data, separators=(',', ':'))
                response = session.post(url, data=data, verify=False)
                location_id = response.json()['data'][0][0]
            except:
                message = 'Location could not be found\n'
                logger.debug(message)
                return message, 400
            try:
                data = {'query': get_product_id_by_uuid, 'params': {'uuid': str(product_uuid)}}
                data = json.dumps(data, separators=(',', ':'))
                response = session.post(url, data=data, verify=False)
                product_id = response.json()['data'][0][0]
            except:
                message = 'Product could not be found\n'
                logger.debug(message)
                return message, 400
            try:
                data = {'query': get_product_details, 'params': {'uuidp': str(product_uuid), 'uuidl': str(location_uuid)}}
                data = json.dumps(data, separators=(',', ':'))
                response = session.post(url, data=data, verify=False)
            except:
                message = 'available_at Relationship could not be found\n'
                logger.debug(message)
                return message, 400

            label = 'Raincheck'
            # Create new node
            url = neo_http_ap + '/db/data/node'
            data = {
                    'uuid' : str(uuid.uuid4()),
                    'serveDate': str(datetime.datetime.now()),
                    'expiryDate': str(expiryDate),
                    'salePrice': salePrice
                    }
            node_data = data
            data = json.dumps(data, separators=(',',':'))
            response = session.post(url, data=data, headers=headers, verify=False)
            if (response.ok):
                logger.info('Successfully created raincheck node: ' + str(response))
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
            if not (response.ok):
                response_dump = None
                try:
                    response_dump = response.json()
                except:
                    response_dump = logger.dump_var(response)
                message = 'Response to label addition not okay:\n%s' % response_dump
                logger.debug(message)
                return message, 400

            #Attach to user
            relationship_type = 'tied_to'
            url = neo_http_ap + '/db/data/node/' + str(new_node_id) + '/relationships'
            data = {'to': neo_bolt_ap + '/db/data/node/' + str(consumer_id), 'type': relationship_type}
            data = json.dumps(data, separators=(',', ':'))
            response = session.post(url, data=data, headers=headers, verify=False)
            if not (response.ok):
                response_dump = None
                try:
                    response_dump = response.json()
                except:
                    response_dump = logger.dump_var(response)
                message = 'Response to POST was not OK:\n%s' % response_dump
                logger.debug(message)
                return message, 400

            # Attach to product
            relationship_type = 'original_product'
            url = neo_http_ap + '/db/data/node/' + str(new_node_id) + '/relationships'
            data = {'to': neo_bolt_ap + '/db/data/node/' + str(product_id), 'type': relationship_type}
            data = json.dumps(data, separators=(',', ':'))
            response = session.post(url, data=data, headers=headers, verify=False)
            if not (response.ok):
                response_dump = None
                try:
                    response_dump = response.json()
                except:
                    response_dump = logger.dump_var(response)
                message = 'Response to POST was not OK:\n%s' % response_dump
                logger.debug(message)
                return message, 400

            # Attach to location
            relationship_type = 'original_store'
            url = neo_http_ap + '/db/data/node/' + str(new_node_id) + '/relationships'
            data = {'to': neo_bolt_ap + '/db/data/node/' + str(location_id), 'type': relationship_type}
            data = json.dumps(data, separators=(',', ':'))
            response = session.post(url, data=data, headers=headers, verify=False)
            if not (response.ok):
                response_dump = None
                try:
                    response_dump = response.json()
                except:
                    response_dump = logger.dump_var(response)
                message = 'Response to POST was not OK:\n%s' % response_dump
                logger.debug(message)
                return message, 400
            return str(node_data), 200
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
        '''Get raincheck node'''
        try:
            args = read_argparser.parse_args()
            url = neo_http_ap + '/db/data/cypher'
            try:
                data = {'query': get_raincheck_id_by_uuid, 'params': {'uuid': str(target_uuid)}}
                data = json.dumps(data, separators=(',', ':'))
                response = session.post(url, data=data, verify=False)
                if (response.ok):
                    target_id = response.json()['data'][0][0]
            except:
                message = 'Raincheck could not be found\n'
                logger.debug(message)
                return message, 400
            responses = []
            url = neo_http_ap + '/db/data/node/' + str(target_id) + '/properties'
            response = session.get(url, verify=False)
            if (response.ok):
                responses.append(response.json())
            else:
                response_dump = None
                try:
                    response_dump = response.json()
                except:
                    response_dump = logger.dump_var(response)
                message = 'Response to raincheck retrieval not OK:\n%s' % response_dump
                logger.debug(message)
                return message, 400
            url = neo_http_ap + '/db/data/node/' + str(target_id) + '/relationships/all'
            response = session.get(url, verify=False)
            if (response.ok):
                for rel in response.json():
                    url = neo_http_ap + '/db/data/relationship/' + str(rel['metadata']['id'])
                    new_response = session.get(url, verify=False)
                    url = str(new_response.json()['end'])
                    new_response = session.get(url, verify=False)
                    responses.append({new_response.json()['metadata']['labels'][0]:new_response.json()['data']})
                    if (not response.ok):
                        try:
                            problem = response.json()
                        except:
                            problem = response
                        return ('Response to relationship manipulation not OK: %s' % str(problem)), 400
            else:
                response_dump = None
                try:
                    response_dump = response.json()
                except:
                    response_dump = logger.dump_var(response)
                message = 'Response to GET on relationships was not OK:\n%s' % response_dump
                logger.debug(message)
                return message, 400

            return responses, 200
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
        '''Delete a consumer by UUID'''
        try:
            try:
                url = neo_http_ap + '/db/data/cypher'
                data = {'query': get_raincheck_id_by_uuid, 'params': {'uuid': str(target_uuid)}}
                data = json.dumps(data, separators=(',', ':'))
                response = session.post(url, data=data, verify=False)
                if (response.ok):
                    target_id = response.json()['data'][0][0]
            except:
                message = 'Consumer could not be found\n'
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
                return {'message': 'Consumer deletion was successful', 'response': str(response)}, 200
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
