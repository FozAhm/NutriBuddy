# ======================================================
# ======================================================
# CONSUMERS
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


logger = SimpleLogger('ConsumersManager', 5)

# orchestrator= os.getenv('Orchestrator_AP' ,'0.0.0.0:5000')
# mongoIP=os.getenv('CMDB_AP' ,'0.0.0.0:27017')
# client = MongoClient(mongoIP.split(":")[0], int(mongoIP.split(":")[1]) , connect=False)
# #client = MongoClient("mongodb://mongodb0.example.net:27017")
# db = client.client

api = Namespace('consumers', description='Neo4j consumer-related operations')

consumers = api.model('consumers', {
    'type': fields.String(description='The resource identifier'),
})

consumers_container = api.model('consumersContainer', {
    'consumers': fields.Nested(consumers),
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
    create_argparser.add_argument('name', type=str, required=False, location='form', help='Consumer name')
    create_argparser.add_argument('email', type=str, required=True, location='form', help='Consumer email')
    create_argparser.add_argument('firebase_id', type=str, required=True, location='form', help='Firebase ID')
    create_argparser.add_argument('firebase_token', type=str, required=True, location='form', help='Token for Firebase notifications')
    create_argparser.add_argument('image_name', type=str, required=False, location='form', help='Image file name')
    # TODO: Allow other properties
    @api.expect(create_argparser)
    @api.doc(responses={
        200: 'Success',
        400: 'Validation Error'
    })
    def post(self, name=None):
        '''Add a consumer'''
        try:
            args = create_argparser.parse_args()
            if args['name']:
                name = args['name']
            else:
                return '`name` is a required field', 400
            if args['email']:
                email = args['email']
            else:
                return '`email` is a required field', 400
            if args['firebase_id']:
                firebase_id = args['firebase_id']
            else:
                return '`firebase_id` is a required field', 400
            if args['firebase_token']:
                firebase_token = args['firebase_token']
            else:
                return '`firebase_token` is a required field', 400
            if args['image_name']:
                image = args['image_name']
            else:
                image = 'null'

            # Get all orgs to attach loyalty trackers to
            #Done here so error does not create incomplete consumer node
            url = neo_http_ap + '/db/data/cypher'
            try:
                data = {'query': get_all_orgs}
                data = json.dumps(data, separators=(',', ':'))
                response = session.post(url, data=data, verify=False)
                orgs = response.json()['data']
            except:
                message = 'Could not get Organizations'
                logger.debug(message)
                return message, 400

            label = 'Consumer'
            # Create new node
            url = neo_http_ap + '/db/data/node'
            data = {
                    'name': name,
                    'email': email,
                    'firebase_id': firebase_id,
                    'firebase_token':firebase_token,
                    'uuid' : str(uuid.uuid4()),
                    'image': image
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
            if not (response.ok):
                response_dump = None
                try:
                    response_dump = response.json()
                except:
                    response_dump = logger.dump_var(response)
                message = 'Response to label addition not okay:\n%s' % response_dump
                logger.debug(message)
                return message, 400

            #Adding the loyalty trackers to each existing organization
            relationship_type = 'loyalty_tracker'
            url = neo_http_ap + '/db/data/node/' + str(new_node_id) + '/relationships'
            for org in orgs:
                data = {'to': neo_bolt_ap + '/db/data/node/' + str(org[0]['metadata']['id']), 'type': relationship_type}
                data['data'] = {'points': '0'}
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

            return {'message': 'Node addition successful', 'response': str(response)}, 200

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
        '''Get a consumer by UUID'''
        try:
            args = read_argparser.parse_args()
            url = neo_http_ap + '/db/data/cypher'
            try:
                data = {'query': get_consumer_id_by_uuid, 'params': {'uuid': str(target_uuid)}}
                data = json.dumps(data, separators=(',', ':'))
                response = session.post(url, data=data, verify=False)
                if (response.ok):
                    target_id = response.json()['data'][0][0]
            except:
                message = 'Consumer could not be found\n'
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

#Get by Firebase ID
read_argparser = argparser.copy()
@api.route('/<string:target_fbid>/get2')
class Read(Resource):
    @api.expect(read_argparser)
    @api.doc(responses={
        200: 'Success',
        400: 'Validation Error'
    })
    def get(self, target_fbid):
        '''Get a consumer by firebase ID'''
        try:
            args = read_argparser.parse_args()
            url = neo_http_ap + '/db/data/cypher'
            try:
                data = {'query': get_consumer_id_by_fbid, 'params': {'fbid': str(target_fbid)}}
                data = json.dumps(data, separators=(',', ':'))
                response = session.post(url, data=data, verify=False)
                if (response.ok):
                    target_fbid = response.json()['data'][0][0]  # Response gives what should be an int as a double array, needs to be 0 indexed twice to isolate
            except:
                message = 'Consumer could not be found\n'
                logger.debug(message)
                return message, 400
            url = neo_http_ap + '/db/data/node/' + str(target_fbid) + '/properties'
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
        '''Get 1000 consumers'''
        try:
            url = neo_http_ap + '/db/data/label/Consumer/nodes'
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
        '''Update consumer node, empty value will delete property'''
        try:
            args = update_argparser.parse_args()
            if args['property']:
                property = args['property']
            else:
                return '`property` is a required field', 400
            url = neo_http_ap + '/db/data/cypher'
            try:
                data = {'query': get_consumer_id_by_uuid, 'params': {'uuid': str(target_uuid)}}
                data = json.dumps(data, separators=(',', ':'))
                response = session.post(url, data=data, verify=False)
                if (response.ok):
                    target_id = response.json()['data'][0][0]  # Response gives what should be an int as a double array, needs to be 0 indexed twice to isolate
            except:
                message = 'Consumer could not be found\n'
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
                message = 'Response to consumer properties retrieval not OK:\n%s' % response_dump
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
                    return {'message': 'Consumer successfully updated', 'response': str(response)}, 200
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
        '''Delete a consumer by UUID'''
        try:
            try:
                url = neo_http_ap + '/db/data/cypher'
                data = {'query': get_consumer_id_by_uuid, 'params': {'uuid': str(target_uuid)}}
                data = json.dumps(data, separators=(',', ':'))
                response = session.post(url, data=data, verify=False)
                if (response.ok):
                    target_id = response.json()['data'][0][0]  # Response gives what should be an int as a double array, needs to be 0 indexed twice to isolate
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


joincommunity_argparser = argparser.copy()
@api.route('/<string:consumer_uuid>/joincommunity')
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
    def put(self, consumer_uuid=None, community_uuid=None, relationship_property=None, property_value=None):
        '''Add a consumer to a community'''
        try:
            args = joincommunity_argparser.parse_args()
            if args['community_uuid']:
                community_uuid = args['community_uuid']
            else:
                return '`community_uuid` is a required field', 400

            # Searching by uuid
            try:
                url = neo_http_ap + '/db/data/cypher'
                data = {'query': get_consumer_id_by_uuid, 'params': {'uuid': str(consumer_uuid)}}
                data = json.dumps(data, separators=(',', ':'))
                response = session.post(url, data=data, verify=False)
                if (response.ok):
                    consumer_id = response.json()['data'][0][0]  # Response gives what should be an int as a double array, needs to be 0 indexed twice to isolate
            except:
                message = 'Consumer could not be found\n'
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

            relationship_type = 'is_member_of'
            # Create new relationship
            url = neo_http_ap + '/db/data/node/' + str(consumer_id) + '/relationships'
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
                    return {'message': 'Consumer successfully added to community', 'response': str(response)}, 200
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
@api.route('/<string:consumer_uuid>/leave_community')
class Leave_Community(Resource):
    leave_community_argparser.add_argument('community_uuid', type=str, required=True, location='form', help='Community node ID')
    @api.expect(leave_community_argparser)
    @api.doc(responses={
        200: 'Success',
        400: 'Validation Error'
    })
    def delete(self, consumer_uuid=None, community_uuid=None,):
        '''Leave a Community'''
        try:
            args = leave_community_argparser.parse_args()
            if args['community_uuid']:
                community_uuid = args['community_uuid']
            else:
                return '`community_uuid` is a required field', 400
            url = neo_http_ap + '/db/data/cypher'
            try:
                data = {'query': get_is_member_of, 'params': {'uuid1': str(consumer_uuid), 'uuid2':str(community_uuid)}}
                data = json.dumps(data, separators=(',', ':'))
                response = session.post(url, data=data, verify=False)
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
                return 'Left community', 200

        except Exception as exc:
            message = 'Something went wrong'
            logger.critical(message)
            logger.dump_exception(exc)
            return message, 500

getcommunities_argparser = argparser.copy()
@api.route('/<string:consumer_uuid>/getcommunities')
class ReadMany(Resource):
    @api.expect(getcommunities_argparser)
    @api.doc(responses={
        200: 'Success',
        400: 'Validation Error'
    })
    def get(self, consumer_uuid):
        '''Get a consumer's communities'''
        try:
            url = neo_http_ap + '/db/data/cypher'
            data = {'query': get_full_communities, 'params': {'uuid': str(consumer_uuid)}}
            data = json.dumps(data, separators=(',', ':'))
            response = session.post(url, data=data, verify=False)
            if (response.ok):
                data = response.json()['data']
                communities = []
                for result in data:
                    communities.append(result[0]['data'])
                return communities, 200
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

addfriend_argparser = argparser.copy()
@api.route('/<string:consumer_uuid>/addfriend')
class AddFriend(Resource):
    addfriend_argparser.add_argument('friend_uuid', type=str, required=True, location='form', help='Consumer (friend) node ID')
    addfriend_argparser.add_argument('relationship_property', type=str, required=False, location='form', help='Property of relationship')
    addfriend_argparser.add_argument('property_value', type=str, required=False, location='form', help='Value of proprety')
    # TODO: Allow a range of properties
    @api.expect(addfriend_argparser)
    @api.doc(responses={
        200: 'Success',
        400: 'Validation Error'
    })
    def put(self, consumer_uuid=None, friend_uuid=None, relationship_property=None, property_value=None):
        '''Add a consumer (friend) to a consumer'''
        try:
            args = addfriend_argparser.parse_args()
            if args['friend_uuid']:
                friend_uuid = args['friend_uuid']
            else:
                return '`friend_uuid` is a required field', 400
            # Searching by uuid
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
                data = {'query': get_consumer_id_by_uuid, 'params': {'uuid': str(friend_uuid)}}
                data = json.dumps(data, separators=(',', ':'))
                response = session.post(url, data=data, verify=False)
                if (response.ok):
                    friend_id = response.json()['data'][0][0]
            except:
                message = 'Consumer could not be found\n'
                logger.debug(message)
                return message, 400

            relationship_type = 'is_friends_with'
            # Create new relationship
            url = neo_http_ap + '/db/data/node/' + str(consumer_id) + '/relationships'
            data = {'to': neo_bolt_ap + '/db/data/node/' + str(friend_id), 'type': relationship_type}
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
                    return {'message': 'Friend successfully added to consumer', 'response': str(response)}, 200
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

delete_friend_argparser = argparser.copy()
@api.route('/<string:consumer_uuid>/delete_friend')
class Delete_Friend(Resource):
    delete_friend_argparser.add_argument('friend_uuid', type=str, required=True, location='form', help='Friend Consumer node ID')
    @api.expect(delete_friend_argparser)
    @api.doc(responses={
        200: 'Success',
        400: 'Validation Error'
    })
    def delete(self, consumer_uuid=None, friend_uuid=None,):
        '''Delete friend'''
        try:
            args = delete_friend_argparser.parse_args()
            if args['friend_uuid']:
                friend_uuid = args['friend_uuid']
            else:
                return '`friend_uuid` is a required field', 400
            url = neo_http_ap + '/db/data/cypher'
            try:
                data = {'query': get_is_friends_with, 'params': {'uuid1': str(consumer_uuid), 'uuid2':str(friend_uuid)}}
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
                return 'Deleted friend', 200

        except Exception as exc:
            message = 'Something went wrong'
            logger.critical(message)
            logger.dump_exception(exc)
            return message, 500

get_friends_argparser = argparser.copy()
@api.route('/<string:consumer_uuid>/getfriends')
class GET_Friend(Resource):
    @api.expect(get_friends_argparser)
    @api.doc(responses={
        200: 'Success',
        400: 'Validation Error'
    })
    def get(self, consumer_uuid=None, friend_uuid=None,):
        '''Get friends'''
        try:
            url = neo_http_ap + '/db/data/cypher'
            try:
                data = {'query': get_all_friends, 'params': {'uuid': str(consumer_uuid)}}
                data = json.dumps(data, separators=(',', ':'))
                response = session.post(url, data=data, verify=False)
                friends = []
                for friend in response.json()['data']:
                    friends.append(friend[0]['data'])
                return friends
            except:
                message = 'Relationship could not be found\n'
                logger.debug(message)
                return message, 400

        except Exception as exc:
            message = 'Something went wrong'
            logger.critical(message)
            logger.dump_exception(exc)
            return message, 500

# TODO: UpdateFriendship

# TODO: UpdateMembership

followorganization_argparser = argparser.copy()
@api.route('/<string:consumer_uuid>/followorganization')
class FollowOrganization(Resource):
    followorganization_argparser.add_argument('organization_uuid', type=str, required=True, location='form', help='Organization node UUID')
    followorganization_argparser.add_argument('relationship_property', type=str, required=False, location='form',help='Property of relationship')
    followorganization_argparser.add_argument('property_value', type=str, required=False, location='form',help='Value of proprety')

    # TODO: Allow a range of properties
    @api.expect(followorganization_argparser)
    @api.doc(responses={
        200: 'Success',
        400: 'Validation Error'
    })
    def put(self, consumer_uuid=None, organization_uuid=None, relationship_property=None, property_value=None):
        '''Set user following orgnization'''
        try:
            args = followorganization_argparser.parse_args()
            if args['organization_uuid']:
                organization_uuid = args['organization_uuid']
            else:
                return '`organization_uuid` is a required field', 400
            # Searching by uuid
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
                data = {'query': get_organization_id_by_uuid, 'params': {'uuid': str(organization_uuid)}}
                data = json.dumps(data, separators=(',', ':'))
                response = session.post(url, data=data, verify=False)
                if (response.ok):
                    organization_id = response.json()['data'][0][0]
            except:
                message = 'Organization could not be found\n'
                logger.debug(message)
                return message, 400
            relationship_type = 'following'
            # Create new relationship
            url = neo_http_ap + '/db/data/node/' + str(consumer_id) + '/relationships'
            data = {'to': neo_bolt_ap + '/db/data/node/' + str(organization_id), 'type': relationship_type}
            if args['relationship_property']:
                relationship_property = args['relationship_property']
                if args['property_value']:
                    property_value = args['property_value']
                    data['data'] = {relationship_property: property_value}
                else:
                    return 'Property needs a value', 400
            data = json.dumps(data, separators=(',', ':'))
            response = session.post(url, data=data, headers=headers, verify=False)
            if (response.ok):
                return {'message': 'User successfully following organization',
                        'response': str(response)}, 200
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

unfollow_org_argparser = argparser.copy()
@api.route('/<string:consumer_uuid>/unfollow_org')
class Unfollow_Org(Resource):
    unfollow_org_argparser.add_argument('organization_uuid', type=str, required=True, location='form', help='Organization node ID')
    @api.expect(unfollow_org_argparser)
    @api.doc(responses={
        200: 'Success',
        400: 'Validation Error'
    })
    def delete(self, consumer_uuid=None, organization_uuid=None,):
        '''Unfollow organization'''
        try:
            args = unfollow_org_argparser.parse_args()
            if args['organization_uuid']:
                organization_uuid = args['organization_uuid']
            else:
                return '`organization_uuid` is a required field', 400
            url = neo_http_ap + '/db/data/cypher'
            try:
                data = {'query': get_following, 'params': {'uuid1': str(consumer_uuid), 'uuid2':str(organization_uuid)}}
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
                return 'Unfollowed organization', 200

        except Exception as exc:
            message = 'Something went wrong'
            logger.critical(message)
            logger.dump_exception(exc)
            return message, 500

eventinterest_argparser = argparser.copy()
@api.route('/<string:consumer_uuid>/eventinterest')
class EventInterest(Resource):
    eventinterest_argparser.add_argument('event_uuid', type=str, required=True, location='form', help='Community node ID')
    eventinterest_argparser.add_argument('going', type=bool, required=False, location='form', help='User planning on going')
    # TODO: Allow a range of properties
    @api.expect(eventinterest_argparser)
    @api.doc(responses={
        200: 'Success',
        400: 'Validation Error'
    })
    def put(self, consumer_uuid=None, event_uuid=None, relationship_property=None, property_value=None):
        '''Consumer interested in Event, Property flag for Going to'''
        try:
            args = eventinterest_argparser.parse_args()
            if args['event_uuid']:
                event_uuid = args['event_uuid']
            else:
                return '`event_uuid` is a required field', 400

            # Searching by uuid
            url = neo_http_ap + '/db/data/cypher'
            try:
                data = {'query': get_consumer_id_by_uuid, 'params': {'uuid': str(consumer_uuid)}}
                data = json.dumps(data, separators=(',', ':'))
                response = session.post(url, data=data, verify=False)
                if (response.ok):
                    consumer_id = response.json()['data'][0][0]  # Response gives what should be an int as a double array, needs to be 0 indexed twice to isolate
            except:
                message = 'Consumer could not be found\n'
                logger.debug(message)
                return message, 400
            try:
                data = {'query': get_event_id_by_uuid, 'params': {'uuid': str(event_uuid)}}
                data = json.dumps(data, separators=(',', ':'))
                response = session.post(url, data=data, verify=False)
                if (response.ok):
                    event_id = response.json()['data'][0][0]  # Response gives what should be an int as a double array, needs to be 0 indexed twice to isolate
            except:
                message = 'Event could not be found\n'
                logger.debug(message)
                return message, 400

            relationship_type = 'interested_in' #Maybe change to isolate from other kinds of interested in relationships
            # Create new relationship
            url = neo_http_ap + '/db/data/node/' + str(consumer_id) + '/relationships'
            data = {'to': neo_bolt_ap + '/db/data/node/' + str(event_id), 'type': relationship_type}
            if args['going']:
                going = args['going']
            else:
                going = False
            data['data'] = {'going': going}
            data = json.dumps(data, separators=(',',':'))
            response = session.post(url, data=data, headers=headers, verify=False)
            if (response.ok):
                    return {'message': 'Sucessfully added user interested in event', 'response': str(response)}, 200
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

delete_eventinterest_argparser = argparser.copy()
@api.route('/<string:consumer_uuid>/delete_event_interest')
class Delete_EventInterest(Resource):
    delete_eventinterest_argparser.add_argument('event_uuid', type=str, required=True, location='form', help='Event node ID')
    @api.expect(delete_eventinterest_argparser)
    @api.doc(responses={
        200: 'Success',
        400: 'Validation Error'
    })
    def delete(self, consumer_uuid=None, event_uuid=None,):
        '''Remove event customer's interested in or going to event'''
        try:
            args = delete_eventinterest_argparser.parse_args()
            if args['event_uuid']:
                event_uuid = args['event_uuid']
            else:
                return '`event_uuid` is a required field', 400
            url = neo_http_ap + '/db/data/cypher'
            try:
                data = {'query': get_interested_in, 'params': {'uuid1': str(consumer_uuid), 'uuid2':str(event_uuid)}}
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
                return 'Removed interest in event', 200

        except Exception as exc:
            message = 'Something went wrong'
            logger.critical(message)
            logger.dump_exception(exc)
            return message, 500

wishlist_argparser = argparser.copy()
@api.route('/<string:consumer_uuid>/wlproduct')
class Wishlist(Resource):
    wishlist_argparser.add_argument('product_uuid', type=str, required=True, location='form', help='Product node ID')
    # TODO: Allow a range of properties
    @api.expect(wishlist_argparser)
    @api.doc(responses={
        200: 'Success',
        400: 'Validation Error'
    })
    def put(self, consumer_uuid=None):
        '''Consumer wishlisted Product'''
        try:
            args = wishlist_argparser.parse_args()
            if args['product_uuid']:
                product_uuid = args['product_uuid']
            else:
                return '`product_uuid` is a required field', 400
            # Searching by uuid
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

            #cleanup, prevent duplicates
            data = {'query': unique_wishlist, 'params': {'uuidc': str(consumer_uuid), 'uuidp' : str(product_uuid)}}
            data = json.dumps(data, separators=(',', ':'))
            response = session.post(url, data=data, verify=False)

            relationship_type = 'wishlisted'
            # Create new relationship
            url = neo_http_ap + '/db/data/node/' + str(consumer_id) + '/relationships'
            data = {'to': neo_bolt_ap + '/db/data/node/' + str(product_id), 'type': relationship_type}
            data['data'] = {'date': str(datetime.datetime.now())}
            data = json.dumps(data, separators=(',',':'))
            response = session.post(url, data=data, headers=headers, verify=False)
            if (response.ok):
                    return {'message': 'Sucessfully added product to consumer\'s wishlist', 'response': str(response)}, 200
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


delete_wishlist_argparser = argparser.copy()
@api.route('/<string:consumer_uuid>/delete_wishlist')
class Delete_Wishlist(Resource):
    delete_wishlist_argparser.add_argument('product_uuid', type=str, required=True, location='form', help='Product node ID')
    @api.expect(delete_wishlist_argparser)
    @api.doc(responses={
        200: 'Success',
        400: 'Validation Error'
    })
    def delete(self, consumer_uuid=None, product_uuid=None,):
        '''Remove product from customer's wishlist'''
        try:
            args = delete_wishlist_argparser.parse_args()
            if args['product_uuid']:
                product_uuid = args['product_uuid']
            else:
                return '`product_uuid` is a required field', 400
            url = neo_http_ap + '/db/data/cypher'
            try:
                data = {'query': get_wishlisted, 'params': {'uuid1': str(consumer_uuid), 'uuid2':str(product_uuid)}}
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
                return 'Product removed from wishlist', 200

        except Exception as exc:
            message = 'Something went wrong'
            logger.critical(message)
            logger.dump_exception(exc)
            return message, 500


getwishlist_argparser = argparser.copy()
@api.route('/<string:consumer_uuid>/getwishlist')
class ReadMany(Resource):
    @api.expect(readmany_argparser)
    @api.doc(responses={
        200: 'Success',
        400: 'Validation Error'
    })
    def get(self, consumer_uuid):
        '''Get a consumer's wishlist'''
        try:
            url = neo_http_ap + '/db/data/cypher'
            data = {'query': get_full_wishlist, 'params': {'uuid': str(consumer_uuid)}}
            data = json.dumps(data, separators=(',', ':'))
            response = session.post(url, data=data, verify=False)
            if (response.ok):
                data = response.json()['data']
                products = []
                for result in data:
                    product = result[0]['data']
                    products.append(product)
                return products, 200
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

@api.route('/<string:target_uuid>/removetoken')
class RemoveToken(Resource):
    @api.doc(responses={
        200: 'Success',
        400: 'Validation Error'
    })
    def put(self, target_uuid):
        '''Remove a customer's firebase token, for use on logout'''
        try:
            args = update_argparser.parse_args()
            url = neo_http_ap + '/db/data/cypher'
            try:
                data = {'query': get_consumer_id_by_uuid, 'params': {'uuid': str(target_uuid)}}
                data = json.dumps(data, separators=(',', ':'))
                response = session.post(url, data=data, verify=False)
                if (response.ok):
                    target_id = response.json()['data'][0][0]
            except:
                message = 'Consumer could not be found\n'
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
                message = 'Response to consumer properties retrieval not OK:\n%s' % response_dump
                logger.debug(message)
                return message, 400
            node_content = response.json()
            del node_content['firebase_token']

            data = json.dumps(node_content, separators=(',', ':'))
            response = session.put(url, data=data, verify=False)
            if (response.ok):
                    return {'message': 'Token removed', 'response': str(response)}, 200
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

token_argparser = argparser.copy()
@api.route('/<string:target_uuid>/givetoken')
class Token(Resource):
    token_argparser.add_argument('token', type=str, required=True, location='form', help='Product node ID')
    @api.expect(token_argparser)
    @api.doc(responses={
        200: 'Success',
        400: 'Validation Error'
    })
    def put(self, target_uuid):
        '''Grant firebase token in conjunction with onTokenRefresh() on log in'''
        try:
            args = token_argparser.parse_args()
            if args['token']:
                token = args['token']
            else:
                return '`token` is a required field', 400

            url = neo_http_ap + '/db/data/cypher'
            try:
                data = {'query': get_consumer_id_by_uuid, 'params': {'uuid': str(target_uuid)}}
                data = json.dumps(data, separators=(',', ':'))
                response = session.post(url, data=data, verify=False)
                if (response.ok):
                    target_id = response.json()['data'][0][0]
            except:
                message = 'Consumer could not be found\n'
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
                message = 'Response to consumer properties retrieval not OK:\n%s' % response_dump
                logger.debug(message)
                return message, 400
            node_content = response.json()
            node_content['firebase_token'] = str(token)
            data = json.dumps(node_content, separators=(',', ':'))
            response = session.put(url, data=data, verify=False)
            if (response.ok):
                    return {'message': 'Token granted', 'response': str(response)}, 200
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

basket_argparser = argparser.copy()
@api.route('/<string:consumer_uuid>/addtobasket')
class Wishlist(Resource):
    wishlist_argparser.add_argument('product_uuid', type=str, required=True, location='form', help='Product node ID')
    @api.expect(wishlist_argparser)
    @api.doc(responses={
        200: 'Success',
        400: 'Validation Error'
    })
    def put(self, consumer_uuid=None):
        '''Consumer basketed Product'''
        try:
            args = wishlist_argparser.parse_args()
            if args['product_uuid']:
                product_uuid = args['product_uuid']
            else:
                return '`product_uuid` is a required field', 400
            # Searching by uuid
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

            # cleanup, prevent duplicates
            data = {'query': unique_basket, 'params': {'uuidc': str(consumer_uuid), 'uuidp': str(product_uuid)}}
            data = json.dumps(data, separators=(',', ':'))
            response = session.post(url, data=data, verify=False)

            relationship_type = 'basketed'
            # Create new relationship
            url = neo_http_ap + '/db/data/node/' + str(consumer_id) + '/relationships'
            data = {'to': neo_bolt_ap + '/db/data/node/' + str(product_id), 'type': relationship_type}
            data['data'] = {
                            'date': str(datetime.datetime.now()),
                            'got':'False'
                            }

            data = json.dumps(data, separators=(',',':'))
            response = session.post(url, data=data, headers=headers, verify=False)
            if (response.ok):
                    return {'message': 'Sucessfully added product to consumer\'s basket', 'response': str(response)}, 200
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

toggle_basket_argparser = argparser.copy()
@api.route('/<string:consumer_uuid>/togglebasketgot')
class Toggle_Got(Resource):
    toggle_basket_argparser.add_argument('product_uuid', type=str, required=True, location='form', help='Product node ID')
    @api.expect(toggle_basket_argparser)
    @api.doc(responses={
        200: 'Success',
        400: 'Validation Error'
    })
    def put(self, consumer_uuid=None, product_uuid=None,):
        '''Toggle got flag on consumer's basket'''
        try:
            args = toggle_basket_argparser.parse_args()
            if args['product_uuid']:
                product_uuid = args['product_uuid']
            else:
                return '`product_uuid` is a required field', 400
            url = neo_http_ap + '/db/data/cypher'
            try:
                data = {'query': get_basketed, 'params': {'uuid1': str(consumer_uuid), 'uuid2':str(product_uuid)}}
                data = json.dumps(data, separators=(',', ':'))
                response = session.post(url, data=data, verify=False)
                if (response.ok):
                    rel_id = response.json()['data'][0][0]
            except:
                message = 'Relationship could not be found\n'
                logger.debug(message)
                return message, 400
            url = neo_http_ap + '/db/data/relationship/' + str(rel_id) +'/properties'
            response = session.get(url, verify=False)
            if (not response.ok):
                try:
                    problem = response.json()
                except:
                    problem = response
                return ('Response to relationship deletion not OK: %s' % str(problem)), 400

            rel_content = response.json()
            if rel_content['got'] == 'False':
                rel_content['got'] = 'True'
            elif rel_content['got'] == 'True':
                rel_content['got'] = 'False'

            data = json.dumps(rel_content, separators=(',', ':'))
            response = session.put(url, data=data, verify=False)
            if (not response.ok):
                try:
                    problem = response.json()
                except:
                    problem = response
                return ('Response to relationship update not OK: %s' % str(problem)), 400
            else:
                return 'Toggled relationship property', 200

        except Exception as exc:
            message = 'Something went wrong'
            logger.critical(message)
            logger.dump_exception(exc)
            return message, 500

delete_basket_argparser = argparser.copy()
@api.route('/<string:consumer_uuid>/deletebasket')
class Delete_Wishlist(Resource):
    delete_basket_argparser.add_argument('product_uuid', type=str, required=True, location='form', help='Product node ID')
    @api.expect(delete_basket_argparser)
    @api.doc(responses={
        200: 'Success',
        400: 'Validation Error'
    })
    def delete(self, consumer_uuid=None, product_uuid=None,):
        '''Remove product from customer's wishlist'''
        try:
            args = delete_basket_argparser.parse_args()
            if args['product_uuid']:
                product_uuid = args['product_uuid']
            else:
                return '`product_uuid` is a required field', 400
            url = neo_http_ap + '/db/data/cypher'
            try:
                data = {'query': get_basketed, 'params': {'uuid1': str(consumer_uuid), 'uuid2':str(product_uuid)}}
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
                return 'Product removed from basket', 200

        except Exception as exc:
            message = 'Something went wrong'
            logger.critical(message)
            logger.dump_exception(exc)
            return message, 500


getwishlist_argparser = argparser.copy()
@api.route('/<string:consumer_uuid>/getbasket')
class ReadMany(Resource):
    @api.expect(readmany_argparser)
    @api.doc(responses={
        200: 'Success',
        400: 'Validation Error'
    })
    def get(self, consumer_uuid):
        '''Get a consumer's basket'''
        try:
            url = neo_http_ap + '/db/data/cypher'
            data = {'query': get_full_basket, 'params': {'uuid': str(consumer_uuid)}}
            data = json.dumps(data, separators=(',', ':'))
            response = session.post(url, data=data, verify=False)
            if (response.ok):
                data = response.json()['data']
                products = []
                for result in data:
                    product = [result[0]['data'],result[1]['data']]
                    products.append(product)
                return products, 200
            else:
                response_dump = None
                try:
                    response_dump = response.json()
                except:
                    response_dump = logger.dump_var(response)
                message = 'Response to basket retrieval was not OK:\n%s' % response_dump
                logger.debug(message)
                return message, 400
        except Exception as exc:
            message = 'Something went wrong'
            logger.critical(message)
            logger.dump_exception(exc)
            return message, 500

read_rainchecks_argparser = argparser.copy()
@api.route('/<string:target_uuid>/get_rainchecks')
class Read(Resource):
    @api.expect(read_rainchecks_argparser)
    @api.doc(responses={
        200: 'Success',
        400: 'Validation Error'
    })
    def get(self, target_uuid):
        '''Get all consumer's rainchecks'''
        try:
            args = read_rainchecks_argparser.parse_args()
            url = neo_http_ap + '/db/data/cypher'
            try:
                data = {'query': get_raincheck_id_from_tied_to, 'params': {'uuid': str(target_uuid)}}
                data = json.dumps(data, separators=(',', ':'))
                response = session.post(url, data=data, verify=False)
                raincheck_ids = response.json()['data']
            except:
                message = 'Consumer could not be found\n'
                logger.debug(message)
                return message, 400
            responses = []
            for target_id in raincheck_ids:
                my_data = []
                url = neo_http_ap + '/db/data/node/' + str(target_id[0]) + '/properties'
                response = session.get(url, verify=False)
                if (response.ok):
                    my_data.append(response.json())
                else:
                    response_dump = None
                    try:
                        response_dump = response.json()
                    except:
                        response_dump = logger.dump_var(response)
                    message = 'Response to raincheck retrieval not OK:\n%s' % response_dump
                    logger.debug(message)
                    return message, 400
                url = neo_http_ap + '/db/data/node/' + str(target_id[0]) + '/relationships/all'
                response = session.get(url, verify=False)
                if (response.ok):
                    for rel in response.json():
                        url = neo_http_ap + '/db/data/relationship/' + str(rel['metadata']['id'])
                        new_response = session.get(url, verify=False)
                        url = str(new_response.json()['end'])
                        new_response = session.get(url, verify=False)
                        if new_response.json()['metadata']['labels'][0] != 'Consumer':
                            my_data.append({new_response.json()['metadata']['labels'][0]: new_response.json()['data']})
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
                responses.append(my_data)

            return responses, 200
        except Exception as exc:
            message = 'Something went wrong'
            logger.critical(message)
            logger.dump_exception(exc)
            return message, 500

loyaltytracker_argparser = argparser.copy()
@api.route('/<string:consumer_uuid>/addloyaltytracker')
class FollowOrganization(Resource):
    loyaltytracker_argparser.add_argument('organization_uuid', type=str, required=True, location='form', help='Organization node UUID')
    @api.expect(loyaltytracker_argparser)
    @api.doc(responses={
        200: 'Success',
        400: 'Validation Error'
    })
    def put(self, consumer_uuid=None, organization_uuid=None, relationship_property=None, property_value=None):
        '''Set user following orgnization'''
        try:
            args = loyaltytracker_argparser.parse_args()
            if args['organization_uuid']:
                organization_uuid = args['organization_uuid']
            else:
                return '`organization_uuid` is a required field', 400
            # Searching by uuid
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
                data = {'query': get_organization_id_by_uuid, 'params': {'uuid': str(organization_uuid)}}
                data = json.dumps(data, separators=(',', ':'))
                response = session.post(url, data=data, verify=False)
                if (response.ok):
                    organization_id = response.json()['data'][0][0]
            except:
                message = 'Organization could not be found\n'
                logger.debug(message)
                return message, 400
            relationship_type = 'loyalty_tracker'
            url = neo_http_ap + '/db/data/node/' + str(consumer_id) + '/relationships'
            data = {'to': neo_bolt_ap + '/db/data/node/' + str(organization_id), 'type': relationship_type}
            data['data'] = {'points' : '0'}
            data = json.dumps(data, separators=(',', ':'))
            response = session.post(url, data=data, headers=headers, verify=False)
            if (response.ok):
                return {'message': 'Added loyalty tracker','response': str(response)}, 200
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

getloyalty_argparser = argparser.copy()
@api.route('/<string:consumer_uuid>/get_loyalty/<string:organization_uuid>')
class FollowOrganization(Resource):
    @api.expect(getloyalty_argparser)
    @api.doc(responses={
        200: 'Success',
        400: 'Validation Error'
    })
    def get(self, consumer_uuid=None, organization_uuid = None):
        '''Get consumer loyalty points from consumer'''
        try:

            url = neo_http_ap + '/db/data/cypher'
            try:
                data = {'query': get_loyalty_tracker, 'params': {'uuidc': str(consumer_uuid), 'uuido':str(organization_uuid)}}
                data = json.dumps(data, separators=(',', ':'))
                response = session.post(url, data=data, verify=False)
                points = response.json()['data'][0][0]['data']['points']
                return points, 200
            except:
                message = 'Could not properly retrieve relationship'
                logger.debug(message)
                return message, 400

        except Exception as exc:
            message = 'Something went wrong'
            logger.critical(message)
            logger.dump_exception(exc)
            return message, 500

getallloyalty_argparser = argparser.copy()
@api.route('/<string:consumer_uuid>/get_all_loyalty')
class FollowOrganization(Resource):
    @api.expect(getloyalty_argparser)
    @api.doc(responses={
        200: 'Success',
        400: 'Validation Error'
    })
    def get(self, consumer_uuid=None, organization_uuid = None):
        '''Get consumer loyalty points for all locations'''
        try:
            returns = []
            url = neo_http_ap + '/db/data/cypher'
            try:
                data = {'query': get_all_loyalty_tracker, 'params': {'uuid': str(consumer_uuid)}}
                data = json.dumps(data, separators=(',', ':'))
                response = session.post(url, data=data, verify=False)
                results = response.json()['data']
            except:
                message = 'Could not properly retrieve relationship'
                logger.debug(message)
                return message, 400

            for result in results:
                points = result[0]['data']['points']
                location_uuid = result[1]['data']['uuid']
                data = {
                        'points':points,
                        'location_uuid':location_uuid
                        }
                returns.append(data)

            return returns, 200

        except Exception as exc:
            message = 'Something went wrong'
            logger.critical(message)
            logger.dump_exception(exc)
            return message, 500

addpoints_argparser = argparser.copy()
@api.route('/<string:consumer_uuid>/add_loyalty_points')
class Update_Location(Resource):
    addpoints_argparser.add_argument('organization_uuid', type=str, required=True, location='form',help='Organization node uuid')
    addpoints_argparser.add_argument('points', type=str, required=True, location='form', help='Points to add')
    @api.expect(addpoints_argparser)
    @api.doc(responses={
        200: 'Success',
        400: 'Validation Error'
    })
    def put(self, consumer_uuid=None):
        '''Adds points to organization and partnered organizations'''
        try:
            args = addpoints_argparser.parse_args()
            if args['organization_uuid']:
                organization_uuid = args['organization_uuid']
            else:
                return '`organization_uuid` is a required field', 400
            try:
                if args['points']:
                    new_points = float(args['points'])
                else:
                    return '`points` is a required field', 400
            except:
                return'Unexpected data type', 400

            url = neo_http_ap + '/db/data/cypher'
            try:
                data = {'query': get_loyalty_tracker,'params': {'uuidc': str(consumer_uuid), 'uuido': str(organization_uuid)}}
                data = json.dumps(data, separators=(',', ':'))
                response = session.post(url, data=data, verify=False)
                rel_id = response.json()['data'][0][0]['metadata']['id']
                points = int(response.json()['data'][0][0]['data']['points'])
            except:
                message = 'Relationship could not be found'
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
            rel_content = response.json()
            try:
                rel_content['points'] = str( int(points)  + int(new_points) )
            except:
                return 'Unexpected data type', 400
            data = json.dumps(rel_content, separators=(',', ':'))
            response = session.put(url, data=data, verify=False)
            if (not response.ok):
                try:
                    problem = response.json()
                except:
                    problem = response
                    return ('Response to relationship update not OK: %s' % str(problem)), 400


            #Adding points to partnered organizations, 5% per level up to 25%
            url = neo_http_ap + '/db/data/cypher'
            try:
                data = {'query': get_all_partners,'params': {'uuid': str(organization_uuid)}}
                data = json.dumps(data, separators=(',', ':'))
                response = session.post(url, data=data, verify=False)
                responses = response.json()['data']
            except:
                message = 'Could not properly retrieve relationship'
                logger.debug(message)
                return message, 400
            for i in responses:
                url = neo_http_ap + '/db/data/cypher'
                try:
                    organization_uuid = str(i[1]['data']['uuid'])
                    level = str(i[0]['data']['level'])
                    try:
                        if (level =='1'):
                            current_points = int(new_points * 0.05)
                        elif (level == '2'):
                            current_points = int(new_points * 0.10)
                        elif (level == '3'):
                            current_points = int(new_points * 0.15)
                        elif (level == '4'):
                            current_points = int(new_points * 0.20)
                        elif (level == '5'):
                            current_points = int(new_points * 0.25)
                    except:
                        return 'Unexpected data type', 400
                    data = {'query': get_loyalty_tracker,'params': {'uuidc': str(consumer_uuid), 'uuido': str(organization_uuid)}}
                    data = json.dumps(data, separators=(',', ':'))
                    response = session.post(url, data=data, verify=False)
                    rel_id = response.json()['data'][0][0]['metadata']['id']
                    points = int(response.json()['data'][0][0]['data']['points'])
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
                rel_content = response.json()
                try:
                    rel_content['points'] = str(int(points) + current_points)
                except:
                    return 'Unexpected data type', 400
                data = json.dumps(rel_content, separators=(',', ':'))
                response = session.put(url, data=data, verify=False)
                if not (response.ok):
                    try:
                        problem = response.json()
                    except:
                        problem = response
                    return ('Response to relationship update not OK: %s' % str(problem)), 400

            return 'Points added', 200

        except Exception as exc:
            message = 'Something went wrong'
            logger.critical(message)
            logger.dump_exception(exc)
            return message, 500

read_purchases_argparser = argparser.copy()
@api.route('/<string:target_uuid>/getpurchases')
class Read(Resource):
    @api.expect(read_purchases_argparser)
    @api.doc(responses={
        200: 'Success',
        400: 'Validation Error'
    })
    def get(self, target_uuid):
        '''Get all consumer's rainchecks'''
        try:
            args = read_purchases_argparser.parse_args()
            url = neo_http_ap + '/db/data/cypher'
            try:
                data = {'query': get_consumer_purchases, 'params': {'uuid': str(target_uuid)}}
                data = json.dumps(data, separators=(',', ':'))
                response = session.post(url, data=data, verify=False)

            except:
                message = 'Relationships could not be found\n'
                logger.debug(message)
                return message, 400

            purchases = []
            for purchase in response.json()['data']:
                purchases.append(purchase[0]['data'])

            return purchases

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
        '''Return a consumer's Image url'''
        try:
            args = read_argparser.parse_args()
            url = neo_http_ap + '/db/data/cypher'
            try:
                data = {'query': get_consumer_id_by_uuid, 'params': {'uuid': str(target_uuid)}}
                data = json.dumps(data, separators=(',', ':'))
                response = session.post(url, data=data, verify=False)
                if (response.ok):
                    target_id = response.json()['data'][0][0]
            except:
                message = 'Consumer could not be found\n'
                logger.debug(message)
                return message, 400
            url = neo_http_ap + '/db/data/node/' + str(target_id) + '/properties/image'
            response = session.get(url, verify=False)
            if (response.ok):
                filename = response.json()
                if (filename == 'null'):
                    return 'No associated image', 404
                return 'consumers/'+str(filename),200
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