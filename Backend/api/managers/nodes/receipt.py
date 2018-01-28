# ======================================================
# ======================================================
# RECEIPTS
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

logger = SimpleLogger('ReceiptManager', 5)

# orchestrator= os.getenv('Orchestrator_AP' ,'0.0.0.0:5000')
# mongoIP=os.getenv('CMDB_AP' ,'0.0.0.0:27017')
# client = MongoClient(mongoIP.split(":")[0], int(mongoIP.split(":")[1]) , connect=False)
# #client = MongoClient("mongodb://mongodb0.example.net:27017")
# db = client.client

api = Namespace('receipts', description='Neo4j receipt-related operations')

receipts = api.model('receipts', {
    'type': fields.String(description='The resource identifier'),
})

receipts_container = api.model('receiptsContainer', {
    'receipts': fields.Nested(receipts),
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
    create_argparser.add_argument('total_cost', type=str, required=True, location='form', help='Price of transaction')
    create_argparser.add_argument('purchase_uuids', type=str, required=True, location='form',action = 'append', help='list of composite purchases')
    @api.expect(create_argparser)
    @api.doc(responses={
        200: 'Success',
        400: 'Validation Error'
    })
    def post(self, name=None):
        '''Add a receipt'''
        try:
            args = create_argparser.parse_args()
            if args['purchase_uuids']:
                purchase_uuids = args['purchase_uuids']
            else:
                return '`purchase_uuids` is a required field', 400
            if args['total_cost']:
                total_cost = args['total_cost']
            else:
                return '`total_cost` is a required field', 400

            purchase_ids = []
            url = neo_http_ap + '/db/data/cypher'
            for purchase_uuid in purchase_uuids:
                try:
                    data = {'query': get_purchase_id_by_uuid, 'params': {'uuid': str(purchase_uuid)}}
                    data = json.dumps(data, separators=(',', ':'))
                    response = session.post(url, data=data, verify=False)
                    if (response.ok):
                        id = response.json()['data'][0][0]
                        purchase_ids.append(id)
                except:
                    message = 'Purchase could not be found\n'
                    logger.debug(message)
                    return message, 400

            label = 'Receipt'
            node_uuid = str(uuid.uuid4())
            # Create new node
            url = neo_http_ap + '/db/data/node'
            data = {
                    'uuid' : node_uuid,
                    'total_cost': total_cost,
                    'date':str(datetime.datetime.now())
                    }
            data = json.dumps(data, separators=(',',':'))
            response = session.post(url, data=data, headers=headers, verify=False)
            if (response.ok):
                logger.info('Successfully created receipt node: ' + str(response))
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

            # Attaching the composite purchases
            relationship_type = 'composes'
            for purchase_id in purchase_ids:
                url = neo_http_ap + '/db/data/node/' + str(purchase_id) + '/relationships'
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

            return node_uuid, 200

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
        '''Get a receipt by UUID'''
        try:
            args = read_argparser.parse_args()
            url = neo_http_ap + '/db/data/cypher'
            try:
                data = {'query': get_receipt_id_by_uuid, 'params': {'uuid': str(target_uuid)}}
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

getpurchases_argparser = argparser.copy()
@api.route('/<string:receipt_uuid>/getpurchases')
class ReadMany(Resource):
    @api.expect(getpurchases_argparser)
    @api.doc(responses={
        200: 'Success',
        400: 'Validation Error'
    })
    def get(self, receipt_uuid):
        '''Get a receipts's composite purchases'''
        try:
            url = neo_http_ap + '/db/data/cypher'
            data = {'query': get_full_purchases, 'params': {'uuid': str(receipt_uuid)}}
            data = json.dumps(data, separators=(',', ':'))
            response = session.post(url, data=data, verify=False)
            if (response.ok):
                data = response.json()['data']
                purchases = []
                for result in data:
                    purchases.append(result[0]['data']['uuid'])
                return purchases, 200
            else:
                response_dump = None
                try:
                    response_dump = response.json()
                except:
                    response_dump = logger.dump_var(response)
                message = 'Response to wishlist retrieval was not OK:\n%s' % response_dump
                logger.debug(message)
                return message, 400
        except Exception as exc:
            message = 'Something went wrong'
            logger.critical(message)
            logger.dump_exception(exc)
            return message, 500