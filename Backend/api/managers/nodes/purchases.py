# ======================================================
# ======================================================
# PURCHASES
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

logger = SimpleLogger('PurchasesManager', 5)

# orchestrator= os.getenv('Orchestrator_AP' ,'0.0.0.0:5000')
# mongoIP=os.getenv('CMDB_AP' ,'0.0.0.0:27017')
# client = MongoClient(mongoIP.split(":")[0], int(mongoIP.split(":")[1]) , connect=False)
# #client = MongoClient("mongodb://mongodb0.example.net:27017")
# db = client.client

api = Namespace('purchases', description='Neo4j purchase-related operations')

purchases = api.model('purchases', {
    'type': fields.String(description='The resource identifier'),
})

purchases_container = api.model('purchasesContainer', {
    'purchases': fields.Nested(purchases),
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
    create_argparser.add_argument('consumer_uuid', type=str, required=True, location='form', help='Consumer node UUID')
    create_argparser.add_argument('product_uuid', type=str, required=True, location='form', help='Product node UUID')
    create_argparser.add_argument('location_uuid', type=str, required=True, location='form', help='Location node UUID')
    create_argparser.add_argument('cost', type=str, required=True, location='form', help='Price of transaction')
    create_argparser.add_argument('date', type=str, required=False, location='form', help='Format yyyy-mm-dd hour:minute:second')
    @api.expect(create_argparser)
    @api.doc(responses={
        200: 'Success',
        400: 'Validation Error'
    })
    def post(self, name=None):
        '''Create Purchase linking consumer, product, and organization'''
        try:
            args = create_argparser.parse_args()
            if args['consumer_uuid']:
                consumer_uuid = args['consumer_uuid']
            else:
                return '`consumer_uuid` is a required field', 400
            if args['cost']:
                cost = args['cost']
            else:
                return '`cost` is a required field', 400
            if args['product_uuid']:
                product_uuid = args['product_uuid']
            else:
                return '`product_uuid` is a required field', 400
            if args['location_uuid']:
                location_uuid = args['location_uuid']
            else:
                return '`location_uuid` is a required field', 400
            if args['date']:
                date = datetime.datetime.strptime(args['date'], "%Y-%m-%d %H:%M:%S")
            else:
                date = 'null'

            #GEtting IDs from UUIDs
            url = neo_http_ap + '/db/data/cypher'
            try:
                data = {'query': get_consumer_id_by_uuid, 'params': {'uuid': str(consumer_uuid)}}
                data = json.dumps(data, separators=(',', ':'))
                response = session.post(url, data=data, verify=False)
                if (response.ok):
                    consumer_id = response.json()['data'][0][0]
            except:
                message = 'Consumer could not be found\n'
                logger.debug(message)
                return message, 400

            try:
                data = {'query': get_product_id_by_uuid, 'params': {'uuid': str(product_uuid)}}
                data = json.dumps(data, separators=(',', ':'))
                response = session.post(url, data=data, verify=False)
                if (response.ok):
                    product_id = response.json()['data'][0][0]
            except:
                message = 'Product could not be found\n'
                logger.debug(message)
                return message, 400

            try:
                data = {'query': get_location_id_by_uuid, 'params': {'uuid': str(location_uuid)}}
                data = json.dumps(data, separators=(',', ':'))
                response = session.post(url, data=data, verify=False)
                if (response.ok):
                    location_id = response.json()['data'][0][0]
            except:
                message = 'Location could not be found\n'
                logger.debug(message)
                return message, 400

            label = 'Purchase'
            # Create new node
            url = neo_http_ap + '/db/data/node'
            node_uuid = str(uuid.uuid4())
            data = {
                    'uuid' : node_uuid,
                    'consumer_uuid':consumer_uuid,
                    'product_uuid':product_uuid,
                    'location_uuid':location_uuid,
                    'date':str(date),
                    'cost':cost
                    }
            data = json.dumps(data, separators=(',',':'))
            response = session.post(url, data=data, headers=headers, verify=False)
            if (response.ok):
                logger.info('Successfully created consumer node: ' + str(response))
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
                # Adding Relationship to the consumer
                relationship_type = 'bought'
                url = neo_http_ap + '/db/data/node/' + str(consumer_id) + '/relationships'
                data = {'to': neo_bolt_ap + '/db/data/node/' + str(new_node_id), 'type': relationship_type}
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

                # Adding Relationship to the product
                relationship_type = 'bought_item'
                url = neo_http_ap + '/db/data/node/' + str(new_node_id)+ '/relationships'
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

                # Adding Relationship to the location
                relationship_type = 'bought_from'
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

                return node_uuid, 200
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
        '''Get a product by UUID'''
        try:
            args = read_argparser.parse_args()
            url = neo_http_ap + '/db/data/cypher'
            try:
                data = {'query': get_purchase_id_by_uuid, 'params': {'uuid': str(target_uuid)}}
                data = json.dumps(data, separators=(',', ':'))
                response = session.post(url, data=data, verify=False)
                if (response.ok):
                    target_id = response.json()['data'][0][0]
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
                message = 'Response to consumer retrieval not OK:\n%s' % response_dump
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
        '''Get 1000 purchases'''
        try:
            url = neo_http_ap + '/db/data/label/Purchase/nodes'
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
                message = 'Response to consumers retrieval was not OK:\n%s' % response_dump
                logger.debug(message)
                return message, 400
        except Exception as exc:
            message = 'Something went wrong'
            logger.critical(message)
            logger.dump_exception(exc)
            return message, 500
