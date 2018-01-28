# ======================================================
# ======================================================
# ORGANIZATIONS
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

logger = SimpleLogger('OrganizationsManager', 5)

# orchestrator= os.getenv('Orchestrator_AP' ,'0.0.0.0:5000')
# mongoIP=os.getenv('CMDB_AP' ,'0.0.0.0:27017')
# client = MongoClient(mongoIP.split(":")[0], int(mongoIP.split(":")[1]) , connect=False)
# #client = MongoClient("mongodb://mongodb0.example.net:27017")
# db = client.client

api = Namespace('organizations', description='Neo4j organizations-related operations')

organizations = api.model('organizations', {
    'type': fields.String(description='The resource identifier'),
})

organizations_container = api.model('OrganizationsContainer', {
    'organizations': fields.Nested(organizations),
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
    create_argparser.add_argument('name', type=str, required=True, location='form', help='Organization name')
    # TODO: Allow other properties
    @api.expect(create_argparser)
    @api.doc(responses={
        200: 'Success',
        400: 'Validation Error'
    })
    def post(self, name=None):
        '''Add an organization'''
        try:
            args = create_argparser.parse_args()
            if args['name']:
                name = args['name']
            else:
                return '`name` is a required field', 400

            # Get all consumers to attach loyalty trackers to
            # Done here so error does not create incomplete consumer node
            url = neo_http_ap + '/db/data/cypher'
            try:
                data = {'query': get_all_consumers}
                data = json.dumps(data, separators=(',', ':'))
                response = session.post(url, data=data, verify=False)
                consumers = response.json()['data']
            except:
                message = 'Could not get Organizations'
                logger.debug(message)
                return message, 400

            label = 'Organization'
            # Create new node
            url = neo_http_ap + '/db/data/node'
            data = {
                    'name': name,
                    'uuid': str(uuid.uuid4())
                    }
            data = json.dumps(data, separators=(',',':'))
            response = session.post(url, data=data, headers=headers, verify=False)
            if (response.ok):
                logger.info('Successfully created organization node: ' + str(response))
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

            # Adding the loyalty trackers to each existing organization
            relationship_type = 'loyalty_tracker'
            data = {'to': neo_bolt_ap + '/db/data/node/' + str(new_node_id), 'type': relationship_type}
            data['data'] = {'points': '0'}
            data = json.dumps(data, separators=(',', ':'))
            for consumer in consumers:
                url = neo_http_ap + '/db/data/node/' + str(consumer[0]['metadata']['id']) + '/relationships'
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

            return {'message': 'Node addition successful'}, 200

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
        '''Get a organization by UUID'''
        try:
            args = read_argparser.parse_args()
            url = neo_http_ap + '/db/data/cypher'
            try:
                data = {'query': get_organization_id_by_uuid, 'params': {'uuid': str(target_uuid)}}
                data = json.dumps(data, separators=(',', ':'))
                response = session.post(url, data=data, verify=False)
                if (response.ok):
                    target_id = response.json()['data'][0][0]  # Response gives what should be an int as a double array, needs to be 0 indexed twice to isolate
            except:
                message = 'Organization could not be found\n'
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
                message = 'Response to organization retrieval not OK:\n%s' % response_dump
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
        '''Get 1000 organizations'''
        try:
            url = neo_http_ap + '/db/data/label/Organizations/nodes'
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
                message = 'Response to organizations retrieval was not OK:\n%s' % response_dump
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
        '''Update organization node, empty value will delete property'''
        try:
            args = update_argparser.parse_args()
            if args['property']:
                property = args['property']
            else:
                return '`property` is a required field', 400
            url = neo_http_ap + '/db/data/cypher'
            try:
                data = {'query': get_organization_id_by_uuid, 'params': {'uuid': str(target_uuid)}}
                data = json.dumps(data, separators=(',', ':'))
                response = session.post(url, data=data, verify=False)
                if (response.ok):
                    target_id = response.json()['data'][0][0]
            except:
                message = 'Organization could not be found\n'
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
                message = 'Response to organization properties retrieval not OK:\n%s' % response_dump
                logger.debug(message)
                return message, 400
            node_content = response.json()
            if args['value']:
                value = args['value']
                node_content[property] = value
            else:
                node_content[property] ='null'

            data = json.dumps(node_content, separators=(',', ':'))
            response = session.put(url, data=data, verify=False)
            if (response.ok):
                    return {'message': 'Organization successfully updated', 'response': str(response)}, 200
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
        '''Delete an organization by ID'''
        try:
            url = neo_http_ap + '/db/data/cypher'
            try:
                data = {'query': get_organization_id_by_uuid, 'params': {'uuid': str(target_uuid)}}
                data = json.dumps(data, separators=(',', ':'))
                response = session.post(url, data=data, verify=False)
                if (response.ok):
                    target_id = response.json()['data'][0][ 0]  # Response gives what should be an int as a double array, needs to be 0 indexed twice to isolate
            except:
                message = 'Organization could not be found\n'
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
                return {'message': 'Organization deletion was successful', 'response': str(response)}, 200
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

#Should Orgs be in communities?
joincommunity_argparser = argparser.copy()
@api.route('/<string:organization_uuid>/joincommunity')
class JoinCommunity(Resource):
    joincommunity_argparser.add_argument('community_uuid', type=str, required=True, location='form', help='Community node ID')
    joincommunity_argparser.add_argument('relationship_property', type=str, required=False, location='form', help='Property of relationship')
    joincommunity_argparser.add_argument('property_value', type=str, required=False, location='form', help='Value of proprety')
    # TODO: Allow a range of properties
    @api.expect(joincommunity_argparser)
    @api.doc(responses={
        200: 'Success',
        400: 'Validation Error'
    })
    def put(self, organization_uuid=None, community_uuid=None, relationship_property=None, property_value=None):
        '''Add a organization to a community'''
        try:
            args = joincommunity_argparser.parse_args()
            if args['community_uuid']:
                community_uuid = args['community_uuid']
            else:
                return '`community_uuid` is a required field', 400
            # Searching by uuid
            url = neo_http_ap + '/db/data/cypher'
            try:
                data = {'query': get_organization_id_by_uuid, 'params': {'uuid': str(organization_uuid)}}
                data = json.dumps(data, separators=(',', ':'))
                response = session.post(url, data=data, verify=False)
                if (response.ok):
                    organization_id = response.json()['data'][0][0]  # Response gives what should be an int as a double array, needs to be 0 indexed twice to isolate
            except:
                message = 'Organization could not be found\n'
                logger.debug(message)
                return message, 400
            try:
                data = {'query': get_community_id_by_uuid, 'params': {'uuid': str(community_uuid)}}
                data = json.dumps(data, separators=(',', ':'))
                response = session.post(url, data=data, verify=False)
                if (response.ok):
                    community_id = response.json()['data'][0][0]  # Response gives what should be an int as a double array, needs to be 0 indexed twice to isolate
            except:
                message = 'Community could not be found\n'
                logger.debug(message)
                return message, 400

            relationship_type = 'monitors'
            # Create new relationship
            url = neo_http_ap + '/db/data/node/' + str(organization_id) + '/relationships'
            data = {'to': neo_bolt_ap + '/db/data/node/' + str(community_id), 'type': relationship_type}
            if args['relationship_property']:
                relationship_property = args['relationship_property']
                if args['property_value']:
                    property_value = args['property_value']
                    data['data'] = {relationship_property: property_value}
                else:
                    return 'Property needs a value', 400
            data = json.dumps(data, separators=(',',':'))
            response = session.post(url, data=data, headers=headers, verify=False)
            if (response.ok):
                    return {'message': 'Organization successfully added to community', 'response': str(response)}, 200
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


leave_community_argparser = argparser.copy()
@api.route('/<string:organization_uuid>/leave_community')
class Leave_Community(Resource):
    leave_community_argparser.add_argument('community_uuid', type=str, required=True, location='form', help='Community node ID')
    @api.expect(leave_community_argparser)
    @api.doc(responses={
        200: 'Success',
        400: 'Validation Error'
    })
    def delete(self, organization_uuid=None, community_uuid=None,):
        '''Leave a Community'''
        try:
            args = leave_community_argparser.parse_args()
            if args['community_uuid']:
                community_uuid = args['community_uuid']
            else:
                return '`community_uuid` is a required field', 400
            url = neo_http_ap + '/db/data/cypher'
            try:
                data = {'query': get_is_member_of, 'params': {'uuid1': str(organization_uuid), 'uuid2':str(community_uuid)}}
                data = json.dumps(data, separators=(',', ':'))
                response = session.post(url, data=data, verify=False)
                if (response.ok):
                    rel_id = response.json()['data'][0][0]  # Response gives what should be an int as a double array, needs to be 0 indexed twice to isolate
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
                return 'Left community', 200

        except Exception as exc:
            message = 'Something went wrong'
            logger.critical(message)
            logger.dump_exception(exc)
            return message, 500

partner_argparser = argparser.copy()
@api.route('/<string:organization_uuid>/addpartner')
class AddPartner(Resource):
    partner_argparser.add_argument('partner_uuid', type=str, required=True, location='form', help='Partner')
    partner_argparser.add_argument('level', type=str, required=True, location='form', help='1, 2, 3, 4, 5')
    # TODO: Allow a range of properties
    @api.expect(partner_argparser)
    @api.doc(responses={
        200: 'Success',
        400: 'Validation Error'
    })
    def put(self, organization_uuid=None):
        '''Partner Organization'''
        try:
            args = partner_argparser.parse_args()
            if args['partner_uuid']:
                partner_uuid = args['partner_uuid']
            else:
                return '`partner_uuid` is a required field', 400
            if args['level']:
                level = args['level']
            else:
                return '`level` is a required field', 400
            if not (level == '1' or level == '2' or level == '3' or level == '4' or level == '5'):
                return '`Level` must be 1, 2, 3, 4, or 5', 400

            # Searching by uuid
            url = neo_http_ap + '/db/data/cypher'
            try:
                data = {'query': get_organization_id_by_uuid, 'params': {'uuid': str(organization_uuid)}}
                data = json.dumps(data, separators=(',', ':'))
                response = session.post(url, data=data, verify=False)
                if (response.ok):
                    organization_id = response.json()['data'][0][0]
            except:
                message = 'Organization could not be found\n'
                logger.debug(message)
                return message, 400
            try:
                data = {'query': get_organization_id_by_uuid, 'params': {'uuid': str(partner_uuid)}}
                data = json.dumps(data, separators=(',', ':'))
                response = session.post(url, data=data, verify=False)
                if (response.ok):
                    partner_id = response.json()['data'][0][0]
            except:
                message = 'Organization could not be found\n'
                logger.debug(message)
                return message, 400

            # cleanup, prevent duplicates
            data = {'query': unique_partner, 'params': {'uuido': str(organization_uuid), 'uuidp': str(partner_uuid)}}
            data = json.dumps(data, separators=(',', ':'))
            response = session.post(url, data=data, verify=False)

            relationship_type = 'partner'
            # Create new relationship
            url = neo_http_ap + '/db/data/node/' + str(organization_id) + '/relationships'
            data = {'to': neo_bolt_ap + '/db/data/node/' + str(partner_id), 'type': relationship_type}
            data['data'] = {'level': level}
            data = json.dumps(data, separators=(',',':'))
            response = session.post(url, data=data, headers=headers, verify=False)
            if (response.ok):
                    return {'message': 'Organizations successfully partnered', 'response': str(response)}, 200
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

remove_partner_argparser = argparser.copy()
@api.route('/<string:organization_uuid>/removepartner')
class Remove_Branch(Resource):
    remove_partner_argparser.add_argument('partner_uuid', type=str, required=True, location='form', help='Partner node ID')
    @api.expect(remove_partner_argparser)
    @api.doc(responses={
        200: 'Success',
        400: 'Validation Error'
    })
    def delete(self, organization_uuid=None):
        '''Remove a branch location'''
        try:
            args = remove_partner_argparser.parse_args()
            if args['partner_uuid']:
                partner_uuid = args['partner_uuid']
            else:
                return '`partner_uuid` is a required field', 400
            url = neo_http_ap + '/db/data/cypher'
            try:
                data = {'query': get_partner, 'params': {'uuido': str(organization_uuid), 'uuidp': str(partner_uuid)}}
                data = json.dumps(data, separators=(',', ':'))
                response = session.post(url, data=data, verify=False)
                rel_id = response.json()['data'][0][0]['metadata']['id']
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
                return 'Removed patnered organization', 200

        except Exception as exc:
            message = 'Something went wrong'
            logger.critical(message)
            logger.dump_exception(exc)
            return message, 500

update_partner_argparser = argparser.copy()
@api.route('/<string:target_uuid>/update_partner')
class UpdateBranches(Resource):
    update_partner_argparser.add_argument('partner_uuid', type=str, required=True, location='form', help='Partnered organization')
    update_partner_argparser.add_argument('new_level', type=str, required=True, location='form',help='Desired value of level (1,2,3,4,5)')
    @api.expect(update_partner_argparser)
    @api.doc(responses={
        200: 'Success',
        400: 'Validation Error'
    })
    def put(self, target_uuid):
        '''Update branched locations, empty value will delete property'''
        try:
            args = update_partner_argparser.parse_args()
            if args['partner_uuid']:
                partner_uuid = args['partner_uuid']
            else:
                return '`partner_uuid` is a required field', 400
            if args['new_level']:
                level = args['new_level']
            else:
                return '`new_level` is a required field', 400
            if not (level == '1' or level == '2' or level == '3' or level == '4' or level == '5'):
                return '`new_level` must be 1, 2, 3, 4, or 5', 400
            url = neo_http_ap + '/db/data/cypher'
            try:
                data = {'query': get_partner, 'params': {'uuido': str(target_uuid), 'uuidp': str(partner_uuid)}}
                data = json.dumps(data, separators=(',', ':'))
                response = session.post(url, data=data, verify=False)
                rel_id = response.json()['data'][0][0]['metadata']['id']
            except:
                message = 'Relationship could not be found\n'
                logger.debug(message)
                return message, 400

            url = neo_http_ap + '/db/data/relationship/' + str(rel_id) + '/properties'
            data = {'level':level}
            data = json.dumps(data, separators=(',', ':'))
            response = session.put(url, data=data, verify=False)
            if (response.ok):
                return {'message': 'Partnership successfully updated', 'response': str(response)}, 200
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

requestpartner_argparser = argparser.copy()
@api.route('/<string:organization_uuid>/requestpartner')
class RequestPartner(Resource):
    requestpartner_argparser.add_argument('partner_uuid', type=str, required=True, location='form', help='Partner')
    requestpartner_argparser.add_argument('message', type=str, required=False, location='form', help='message')
    # TODO: Allow a range of properties
    @api.expect(requestpartner_argparser)
    @api.doc(responses={
        200: 'Success',
        400: 'Validation Error'
    })
    def put(self, organization_uuid=None):
        '''Ask to partner another Organization'''
        try:
            args = requestpartner_argparser.parse_args()
            if args['partner_uuid']:
                partner_uuid = args['partner_uuid']
            else:
                return '`partner_uuid` is a required field', 400
            if args['message']:
                message = args['message']
            else:
                message = ''

            # Searching by uuid
            url = neo_http_ap + '/db/data/cypher'
            try:
                data = {'query': get_organization_id_by_uuid, 'params': {'uuid': str(organization_uuid)}}
                data = json.dumps(data, separators=(',', ':'))
                response = session.post(url, data=data, verify=False)
                if (response.ok):
                    organization_id = response.json()['data'][0][0]
            except:
                message = 'Organization could not be found\n'
                logger.debug(message)
                return message, 400
            try:
                data = {'query': get_organization_id_by_uuid, 'params': {'uuid': str(partner_uuid)}}
                data = json.dumps(data, separators=(',', ':'))
                response = session.post(url, data=data, verify=False)
                if (response.ok):
                    partner_id = response.json()['data'][0][0]
            except:
                message = 'Organization could not be found\n'
                logger.debug(message)
                return message, 400

            relationship_type = 'pending_partner'
            # Create new relationship
            url = neo_http_ap + '/db/data/node/' + str(organization_id) + '/relationships'
            data = {'to': neo_bolt_ap + '/db/data/node/' + str(partner_id), 'type': relationship_type}
            data['data'] = {
                            'date': str(datetime.datetime.now()),
                            'message': message
                            }
            data = json.dumps(data, separators=(',',':'))
            response = session.post(url, data=data, headers=headers, verify=False)
            if (response.ok):
                    return {'message': 'Partner request created in db', 'response': str(response)}, 200
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


@api.route('/<string:organization_uuid>/getpendingpartners')
class RequestPartner(Resource):
    # TODO: Allow a range of properties
    @api.expect()
    @api.doc(responses={
        200: 'Success',
        400: 'Validation Error'
    })
    def get(self, organization_uuid=None):
        '''Ask to partner another Organization'''
        try:
            # Searching by uuid
            url = neo_http_ap + '/db/data/cypher'
            try:
                data = {'query': get_requested_partners, 'params': {'uuid': str(organization_uuid)}}
                data = json.dumps(data, separators=(',', ':'))
                response = session.post(url, data=data, verify=False)
                partners = response.json()['data']
            except:
                message = 'Organization could not be found\n'
                logger.debug(message)
                return message, 400

            responses = []
            for partner in partners:
                responses.append(partner[0]['data'])
            return responses, 200

        except Exception as exc:
            message = 'Something went wrong'
            logger.critical(message)
            logger.dump_exception(exc)
            return message, 500


@api.route('/<string:organization_uuid>/getpartnerrequests')
class RequestPartner(Resource):
    # TODO: Allow a range of properties
    @api.expect()
    @api.doc(responses={
        200: 'Success',
        400: 'Validation Error'
    })
    def get(self, organization_uuid=None):
        '''Ask to partner another Organization'''
        try:
            # Searching by uuid
            url = neo_http_ap + '/db/data/cypher'
            try:
                data = {'query': get_partner_requests, 'params': {'uuid': str(organization_uuid)}}
                data = json.dumps(data, separators=(',', ':'))
                response = session.post(url, data=data, verify=False)
                partners = response.json()['data']
            except:
                message = 'Organization could not be found\n'
                logger.debug(message)
                return message, 400

            responses = []
            for partner in partners:
                responses.append(partner[0]['data'])
            return responses, 200

        except Exception as exc:
            message = 'Something went wrong'
            logger.critical(message)
            logger.dump_exception(exc)
            return message, 500


@api.route('/<string:organization_uuid>/<string:partner_uuid>/getpendingpartnersrelationship')
class RequestPartner(Resource):
    # TODO: Allow a range of properties
    @api.expect()
    @api.doc(responses={
        200: 'Success',
        400: 'Validation Error'
    })
    def get(self, organization_uuid=None, partner_uuid =  None):
        '''Ask to partner another Organization'''
        try:
            # Searching by uuid
            url = neo_http_ap + '/db/data/cypher'
            try:
                data = {'query': get_pending_partner, 'params': {'uuido': str(organization_uuid), 'uuidp':str(partner_uuid)}}
                data = json.dumps(data, separators=(',', ':'))
                response = session.post(url, data=data, verify=False)
                rel = response.json()['data'][0][0]['data']
                return rel
            except:
                message = 'Organization could not be found\n'
                logger.debug(message)
                return message, 400



        except Exception as exc:
            message = 'Something went wrong'
            logger.critical(message)
            logger.dump_exception(exc)
            return message, 500

remove_pending_partner_argparser = argparser.copy()
@api.route('/<string:organization_uuid>/removependingpartner')
class Remove_Branch(Resource):
    remove_partner_argparser.add_argument('partner_uuid', type=str, required=True, location='form', help='Partner node ID')
    @api.expect(remove_partner_argparser)
    @api.doc(responses={
        200: 'Success',
        400: 'Validation Error'
    })
    def delete(self, organization_uuid=None):
        '''Remove a branch location'''
        try:
            args = remove_partner_argparser.parse_args()
            if args['partner_uuid']:
                partner_uuid = args['partner_uuid']
            else:
                return '`partner_uuid` is a required field', 400
            url = neo_http_ap + '/db/data/cypher'
            try:
                data = {'query': get_pending_partner, 'params': {'uuido': str(organization_uuid), 'uuidp': str(partner_uuid)}}
                data = json.dumps(data, separators=(',', ':'))
                response = session.post(url, data=data, verify=False)
                rel_id = response.json()['data'][0][0]['metadata']['id']
            except:
                message = 'Relationship could not be found'
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
                return 'Removed patnered organization', 200

        except Exception as exc:
            message = 'Something went wrong'
            logger.critical(message)
            logger.dump_exception(exc)
            return message, 500

addbranch_argparser = argparser.copy()
@api.route('/<string:organization_uuid>/addbranch')
class AddPresence(Resource):
    addbranch_argparser.add_argument('location_uuid', type=str, required=True, location='form', help='Location node ID')
    addbranch_argparser.add_argument('relationship_property', type=str, required=False, location='form', help='Property of relationship')
    addbranch_argparser.add_argument('property_value', type=str, required=False, location='form', help='Value of proprety')
    # TODO: Allow a range of properties
    @api.expect(addbranch_argparser)
    @api.doc(responses={
        200: 'Success',
        400: 'Validation Error'
    })
    def put(self, organization_uuid=None, location_uuid=None, relationship_property=None, property_value=None):
        '''Add presence of organization at location'''
        try:
            args = addbranch_argparser.parse_args()
            if args['location_uuid']:
                location_uuid = args['location_uuid']
            else:
                return '`location_id` is a required field', 400
            # Searching by uuid
            url = neo_http_ap + '/db/data/cypher'
            try:
                data = {'query': get_organization_id_by_uuid, 'params': {'uuid': str(organization_uuid)}}
                data = json.dumps(data, separators=(',', ':'))
                response = session.post(url, data=data, verify=False)
                if (response.ok):
                    organization_id = response.json()['data'][0][0]
            except:
                message = 'Organization could not be found\n'
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
            relationship_type = 'branched'
            # Create new relationship
            url = neo_http_ap + '/db/data/node/' + str(organization_id) + '/relationships'
            data = {'to': neo_bolt_ap + '/db/data/node/' + str(location_id), 'type': relationship_type}
            if args['relationship_property']:
                relationship_property = args['relationship_property']
                if args['property_value']:
                    property_value = args['property_value']
                    data['data'] = {relationship_property: property_value}
                else:
                    return 'Property needs a value', 400
            data = json.dumps(data, separators=(',',':'))
            response = session.post(url, data=data, headers=headers, verify=False)
            if (response.ok):
                    return {'message': 'Presence successfully added to location', 'response': str(response)}, 200
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

remove_branch_argparser = argparser.copy()
@api.route('/<string:organization_uuid>/remove_branch')
class Remove_Branch(Resource):
    remove_branch_argparser.add_argument('location_uuid', type=str, required=True, location='form', help='location node ID')
    @api.expect(remove_branch_argparser)
    @api.doc(responses={
        200: 'Success',
        400: 'Validation Error'
    })
    def delete(self, organization_uuid=None, location_uuid=None, ):
        '''Remove a branch location'''
        try:
            args = remove_branch_argparser.parse_args()
            if args['location_uuid']:
                location_uuid = args['location_uuid']
            else:
                return '`location_uuid` is a required field', 400
            url = neo_http_ap + '/db/data/cypher'
            try:
                data = {'query': get_branched, 'params': {'uuid1': str(organization_uuid), 'uuid2': str(location_uuid)}}
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
                return 'Removed branch location', 200

        except Exception as exc:
            message = 'Something went wrong'
            logger.critical(message)
            logger.dump_exception(exc)
            return message, 500

update_branch_argparser = argparser.copy()
@api.route('/<string:target_uuid>/update_branches')
class UpdateBranches(Resource):
    update_branch_argparser.add_argument('property', type=str, required=True, location='form', help='Field to be updated')
    update_branch_argparser.add_argument('value', type=str, required=False, location='form',help='Desired value of field')
    @api.expect(update_branch_argparser)
    @api.doc(responses={
        200: 'Success',
        400: 'Validation Error'
    })
    def put(self, target_uuid, property = None, value = None):
        '''Update branched locations, empty value will delete property'''
        try:
            args = update_branch_argparser.parse_args()
            if args['property']:
                property = args['property']
            else:
                return '`property` is a required field', 400
            url = neo_http_ap + '/db/data/cypher'
            try:
                data = {'query': get_branches_id, 'params': {'uuid': str(target_uuid)}}
                data = json.dumps(data, separators=(',', ':'))
                response = session.post(url, data=data, verify=False)
                location_ids = response.json()['data']
            except:
                message = 'Organization could not be found\n'
                logger.debug(message)
                return message, 400

            for location in location_ids:
                url = neo_http_ap + '/db/data/node/' + str(location[0]) + '/properties'
                response = session.get(url, verify = False)
                if not (response.ok):
                    response_dump = None
                    try:
                        response_dump = response.json()
                    except:
                        response_dump = logger.dump_var(response)
                    message = 'Response to organization properties retrieval not OK:\n%s' % response_dump
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
                if not (response.ok):
                    response_dump = None
                    try:
                        response_dump = response.json()
                    except:
                        response_dump = logger.dump_var(response)
                    message = 'Response to update was not OK:\n%s' % response_dump
                    logger.debug(message)
                    return message, 400

            return 'Branches successfully updated', 200

        except Exception as exc:
            message = 'Something went wrong'
            logger.critical(message)
            logger.dump_exception(exc)
            return message, 500

update_branch_availabilty_argparser = argparser.copy()
@api.route('/<string:target_uuid>/update_branch_availabilty')
class UpdateBranches(Resource):
    update_branch_availabilty_argparser.add_argument('product_uuid', type=str, required=True, location='form', help='Product availability to be updated')
    update_branch_availabilty_argparser.add_argument('property', type=str, required=True, location='form', help='Field to be updated')
    update_branch_availabilty_argparser.add_argument('value', type=str, required=False, location='form',help='Desired value of field')
    @api.expect(update_branch_availabilty_argparser)
    @api.doc(responses={
        200: 'Success',
        400: 'Validation Error'
    })
    def put(self, target_uuid, property = None, value = None):
        '''Update branched locations offering products, empty value will delete property'''
        try:
            args = update_branch_availabilty_argparser.parse_args()
            if args['property']:
                property = args['property']
            else:
                return '`property` is a required field', 400
            if args['product_uuid']:
                product_uuid = args['product_uuid']
            else:
                return '`product_uuid` is a required field', 400
            url = neo_http_ap + '/db/data/cypher'
            try:
                data = {'query': get_branches_aa_id, 'params': {'uuido': str(target_uuid), 'uuidp': str(product_uuid)}}
                data = json.dumps(data, separators=(',', ':'))
                response = session.post(url, data=data, verify=False)
                available_at_ids = response.json()['data']
            except:
                message = 'Organization or product could not be found\n'
                logger.debug(message)
                return message, 400

            for available_at in available_at_ids:
                url = neo_http_ap + '/db/data/relationship/' + str(available_at[0]) + '/properties'
                response = session.get(url, verify = False)
                if not (response.ok):
                    response_dump = None
                    try:
                        response_dump = response.json()
                    except:
                        response_dump = logger.dump_var(response)
                    message = 'Response to organization properties retrieval not OK:\n%s' % response_dump
                    logger.debug(message)
                    return message, 400
                rel_content = response.json()
                if args['value']:
                    value = args['value']
                    rel_content[property] = value
                else:
                    rel_content[property] = 'null'

                data = json.dumps(rel_content, separators=(',', ':'))
                response = session.put(url, data=data, verify=False)
                if not (response.ok):
                    response_dump = None
                    try:
                        response_dump = response.json()
                    except:
                        response_dump = logger.dump_var(response)
                    message = 'Response to update was not OK:\n%s' % response_dump
                    logger.debug(message)
                    return message, 400

            return 'Branches offering product successfully updated', 200

        except Exception as exc:
            message = 'Something went wrong'
            logger.critical(message)
            logger.dump_exception(exc)
            return message, 500

branch_add_aa_argparser = argparser.copy()
@api.route('/<string:target_uuid>/addbranchproduct')
class UpdateBranches(Resource):
    update_branch_availabilty_argparser.add_argument('product_uuid', type=str, required=True, location='form', help='Product availability to be added')
    update_branch_availabilty_argparser.add_argument('price', type=str, required=True, location='form', help='Product price')
    @api.expect(branch_add_aa_argparser)
    @api.doc(responses={
        200: 'Success',
        400: 'Validation Error'
    })
    def put(self, target_uuid, product_uuid = None):
        '''Update branched locations, empty value will delete property'''
        try:
            args = branch_add_aa_argparser.parse_args()
            if args['product_uuid']:
                product_uuid = args['product_uuid']
            else:
                return '`product_uuid` is a required field', 400
            if args['price']:
                price = args['price']
            else:
                return '`price` is a required field', 400
            url = neo_http_ap + '/db/data/cypher'
            try:
                data = {'query': get_branches_id, 'params': {'uuid': str(target_uuid)}}
                data = json.dumps(data, separators=(',', ':'))
                response = session.post(url, data=data, verify=False)
                location_ids = response.json()['data']
            except:
                message = 'Organization could not be found\n'
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

            relationship_type = 'available_at'
            stock = "null"
            beacon_id = "null"
            for location_id in location_ids:
                # Create new relationship
                url = neo_http_ap + '/db/data/node/' + str(product_id) + '/relationships'
                data = {'to': neo_bolt_ap + '/db/data/node/' + str(location_id[0]), 'type': relationship_type}
                data['data'] = {
                                'stock': stock,
                                'base_price': price,
                                'price_multiplier': '1.0',
                                'beacon_id': beacon_id
                                }
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

            return 'Product available at branches successfully updated', 200

        except Exception as exc:
            message = 'Something went wrong'
            logger.critical(message)
            logger.dump_exception(exc)
            return message, 500
#TODO: Allow organizations to remove available_at to all branches
