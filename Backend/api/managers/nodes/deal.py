# ======================================================
# ======================================================
# deals
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


logger = SimpleLogger('DealsManager', 5)

# orchestrator= os.getenv('Orchestrator_AP' ,'0.0.0.0:5000')
# mongoIP=os.getenv('CMDB_AP' ,'0.0.0.0:27017')
# client = MongoClient(mongoIP.split(":")[0], int(mongoIP.split(":")[1]) , connect=False)
# #client = MongoClient("mongodb://mongodb0.example.net:27017")
# db = client.client

api = Namespace('deals', description='Neo4j raincheck-related operations')

deals = api.model('deals', {
    'type': fields.String(description='The resource identifier'),
})

deals_container = api.model('dealsContainer', {
    'deals': fields.Nested(deals),
})

session = requests.Session()
headers = {'Content-Type': 'multipart/form-data', 'Accept': 'application/json'}
session.auth = (username, password)

argparser = reqparse.RequestParser()


# ======================================================
# CLASSES
# ======================================================

# # TODO: Change returns for Neo 404s
# create_argparser = argparser.copy()
# @api.route('/add')
# class Create(Resource):
#     create_argparser.add_argument('organization_uuid', type=str, required=True, location='form', help='organization id')
#     create_argparser.add_argument('partner_org_uuid', type=str, required=True, location='form', help='partner organization id')
#     # create_argparser.add_argument('location_uuids', type=str, required=True, action = 'append', location='form', help='organization id')
#     # create_argparser.add_argument('partner_location_uuid', type=str, required=True,action = 'append', location='form', help='organization id')
#     create_argparser.add_argument('expiryDate', type=str, required=True, location='form', help='Format yyyy-mm-dd hour:minute')
#     create_argparser.add_argument('salePrice', type=str, required=True, location='form', help='Price to be given')
#     # TODO: Allow other properties
#     @api.expect(create_argparser)
#     @api.doc(responses={
#         200: 'Success',
#         400: 'Validation Error'
#     })
#     def post(self, name=None):
#         '''Add a deal'''
#         try:
#             args = create_argparser.parse_args()
#             if args['organization_uuid']:
#                 organization_uuid = args['organzation_uuid']
#             else:
#                 return '`organization_uuid` is a required field', 400
#             if args['partner_org_uuid']:
#                 partner_org_uuid = args['partner_org_uuid']
#             else:
#                 return '`partner_org_uuid` is a required field', 400
#             # if args['location_uuids']:
#             #     location_uuids = args['location_uuids']
#             # else:
#             #     return '`location_uuids` is a required field', 400
#             # if args['partner_location_uuids']:
#             #     partner_location_uuids = args['partner_location_uuids']
#             # else:
#             #     return '`partner_location_uuids` is a required field', 400
#             if args['product_uuid']:
#                 product_uuid = args['product_uuid']
#             else:
#                 return '`product_uuid` is a required field', 400
#             if args['expiryDate']:
#                 expiryDate = datetime.datetime.strptime(args['expiryDate'],"%Y-%m-%d %H:%M")
#             else:
#                 return '`expiryDate` is a required field', 400
#             if args['salePrice']:
#                 salePrice = args['salePrice']
#             else:
#                 return '`salePrice` is a required field', 400
#
#             try:
#                 url = neo_http_ap + '/db/data/cypher'
#                 data = {'query': get_organization_id_by_uuid, 'params': {'uuid': str(organization_uuid)}}
#                 data = json.dumps(data, separators=(',', ':'))
#                 response = session.post(url, data=data, verify=False)
#                 organization_id = response.json()['data'][0][0]
#             except:
#                 message = 'Consumer could not be found\n'
#                 logger.debug(message)
#                 return message, 400
#             try:
#                 data = {'query': get_location_id_by_uuid, 'params': {'uuid': str(location_uuid)}}
#                 data = json.dumps(data, separators=(',', ':'))
#                 response = session.post(url, data=data, verify=False)
#                 location_id = response.json()['data'][0][0]
#             except:
#                 message = 'Location could not be found\n'
#                 logger.debug(message)
#                 return message, 400
#             try:
#                 data = {'query': get_product_id_by_uuid, 'params': {'uuid': str(product_uuid)}}
#                 data = json.dumps(data, separators=(',', ':'))
#                 response = session.post(url, data=data, verify=False)
#                 product_id = response.json()['data'][0][0]
#             except:
#                 message = 'Product could not be found\n'
#                 logger.debug(message)
#                 return message, 400
#             try:
#                 data = {'query': get_product_details, 'params': {'uuidp': str(product_uuid), 'uuidl': str(location_uuid)}}
#                 data = json.dumps(data, separators=(',', ':'))
#                 response = session.post(url, data=data, verify=False)
#             except:
#                 message = 'available_at Relationship could not be found\n'
#                 logger.debug(message)
#                 return message, 400
#
#             label = 'Raincheck'
#             # Create new node
#             url = neo_http_ap + '/db/data/node'
#             data = {
#                     'uuid' : str(uuid.uuid4()),
#                     'serveDate': str(datetime.datetime.now()),
#                     'expiryDate': str(expiryDate),
#                     'salePrice': salePrice
#                     }
#             node_data = data
#             data = json.dumps(data, separators=(',',':'))
#             response = session.post(url, data=data, headers=headers, verify=False)
#             if (response.ok):
#                 logger.info('Successfully created raincheck node: ' + str(response))
#             else:
#                 response_dump = None
#                 try:
#                     response_dump = response.json()
#                 except:
#                     response_dump = logger.dump_var(response)
#                 message = 'Response to node addition not OK:\n%s' % response_dump
#                 logger.debug(message)
#                 return message, 400
#
#             # Label newly-created node
#             jsondata = json.loads(response.content)
#             new_node_id = jsondata['metadata']['id']
#             url = neo_http_ap + '/db/data/node/' + str(new_node_id) + '/labels'
#             data = [label]
#             data = json.dumps(data, separators=(',',':'))
#             logger.debug('Data to send: ' + data)
#             response = session.post(url, data=data, headers=headers, verify=False)
#             if not (response.ok):
#                 response_dump = None
#                 try:
#                     response_dump = response.json()
#                 except:
#                     response_dump = logger.dump_var(response)
#                 message = 'Response to label addition not okay:\n%s' % response_dump
#                 logger.debug(message)
#                 return message, 400
#
#             #Attach to user
#             relationship_type = 'tied_to'
#             url = neo_http_ap + '/db/data/node/' + str(new_node_id) + '/relationships'
#             data = {'to': neo_bolt_ap + '/db/data/node/' + str(consumer_id), 'type': relationship_type}
#             data = json.dumps(data, separators=(',', ':'))
#             response = session.post(url, data=data, headers=headers, verify=False)
#             if not (response.ok):
#                 response_dump = None
#                 try:
#                     response_dump = response.json()
#                 except:
#                     response_dump = logger.dump_var(response)
#                 message = 'Response to POST was not OK:\n%s' % response_dump
#                 logger.debug(message)
#                 return message, 400
#
#             # Attach to product
#             relationship_type = 'original_product'
#             url = neo_http_ap + '/db/data/node/' + str(new_node_id) + '/relationships'
#             data = {'to': neo_bolt_ap + '/db/data/node/' + str(product_id), 'type': relationship_type}
#             data = json.dumps(data, separators=(',', ':'))
#             response = session.post(url, data=data, headers=headers, verify=False)
#             if not (response.ok):
#                 response_dump = None
#                 try:
#                     response_dump = response.json()
#                 except:
#                     response_dump = logger.dump_var(response)
#                 message = 'Response to POST was not OK:\n%s' % response_dump
#                 logger.debug(message)
#                 return message, 400
#
#             # Attach to location
#             relationship_type = 'original_store'
#             url = neo_http_ap + '/db/data/node/' + str(new_node_id) + '/relationships'
#             data = {'to': neo_bolt_ap + '/db/data/node/' + str(location_id), 'type': relationship_type}
#             data = json.dumps(data, separators=(',', ':'))
#             response = session.post(url, data=data, headers=headers, verify=False)
#             if not (response.ok):
#                 response_dump = None
#                 try:
#                     response_dump = response.json()
#                 except:
#                     response_dump = logger.dump_var(response)
#                 message = 'Response to POST was not OK:\n%s' % response_dump
#                 logger.debug(message)
#                 return message, 400
#             return str(node_data), 200
#         except Exception as exc:
#             message = 'Something went wrong'
#             logger.critical(message)
#             logger.dump_exception(exc)
#             return message, 500