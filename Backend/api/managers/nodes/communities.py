# ======================================================
# ======================================================
# COMMUNITIES
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

logger = SimpleLogger('CommunitiesManager', 5)

# orchestrator= os.getenv('Orchestrator_AP' ,'0.0.0.0:5000')
# mongoIP=os.getenv('CMDB_AP' ,'0.0.0.0:27017')
# client = MongoClient(mongoIP.split(":")[0], int(mongoIP.split(":")[1]) , connect=False)
# #client = MongoClient("mongodb://mongodb0.example.net:27017")
# db = client.client

api = Namespace('communities', description='Neo4j community-related operations')

communities = api.model('communities', {
    'type': fields.String(description='The resource identifier'),
})

communities_container = api.model('communitiesContainer', {
    'communities': fields.Nested(communities),
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
    create_argparser.add_argument('name', type=str, required=True, location='form', help='Community name')
    create_argparser.add_argument('image_name', type=str, required=False, location='form', help='Image file name')
    create_argparser.add_argument('topic_key', type=str, required=True, location='form', help='Firebase topic')
    # TODO: Allow other properties
    @api.expect(create_argparser)
    @api.doc(responses={
        200: 'Success',
        400: 'Validation Error'
    })
    def post(self, name=None):
        '''Add a community'''
        try:
            args = create_argparser.parse_args()
            if args['name']:
                name = args['name']
            else:
                return '`name` is a required field', 400
            if args['topic_key']:
                topic_key = args['topic_key']
            else:
                return '`topic_key` is a required field', 400
            if args['image_name']:
                image = args['image_name']
            else:
                image = 'null'
            label = 'Community'
            # Create new node
            url = neo_http_ap + '/db/data/node'
            data = {
                    'name': name,
                    'uuid':  str(uuid.uuid4()),
                    'image': image,
                    'topic_key': topic_key
                    }
            data = json.dumps(data, separators=(',',':'))
            response = session.post(url, data=data, headers=headers, verify=False)
            if (response.ok):
                logger.info({'message': 'Successfully created community node: ', 'response': str(response)})
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
        '''Get a community by UUID'''
        try:
            args = read_argparser.parse_args()
            try:
                response_dump = None
                url = neo_http_ap + '/db/data/cypher'
                data = {'query': get_community_id_by_uuid, 'params': {'uuid': str(target_uuid)}}
                data = json.dumps(data, separators=(',', ':'))
                response = session.post(url, data=data, verify=False)
                if (response.ok):
                    target_id = response.json()['data'][0][0] #Response gives what should be an int as a double array, needs to be 0 indexed twice to isolate
            except:
                message = 'Community could not be found\n'
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
                message = 'Response to community retrieval not OK:\n%s' % response_dump
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
        '''Get 1000 communities'''
        try:
            url = neo_http_ap + '/db/data/label/Community/nodes'
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
        '''Update community node, empty value will delete property'''
        try:
            args = update_argparser.parse_args()
            if args['property']:
                property = args['property']
            else:
                return '`property` is a required field', 400
            url = neo_http_ap + '/db/data/cypher'
            try:
                data = {'query': get_community_id_by_uuid, 'params': {'uuid': str(target_uuid)}}
                data = json.dumps(data, separators=(',', ':'))
                response = session.post(url, data=data, verify=False)
                if (response.ok):
                    target_id = response.json()['data'][0][0]  # Response gives what should be an int as a double array, needs to be 0 indexed twice to isolate
            except:
                message = 'Community could not be found\n'
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
                message = 'Response to community properties retrieval not OK:\n%s' % response_dump
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
                    return {'message': 'Community successfully updated', 'response': str(response)}, 200
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
        '''Delete a community by ID'''
        try:
            # Get and delete all relationships of node first
            try:
                url = neo_http_ap + '/db/data/cypher'
                data = {'query': get_community_id_by_uuid, 'params': {'uuid': str(target_uuid)}}
                data = json.dumps(data, separators=(',', ':'))
                response = session.post(url, data=data, verify=False)
                if (response.ok):
                    target_id = response.json()['data'][0][0]  # Response gives what should be an int as a double array, needs to be 0 indexed twice to isolate
            except:
                message = 'Community could not be found\n'
                logger.debug(message)
                return message, 400
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
                return {'message': 'Community deletion was successful', 'response': str(response)}, 200
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


addpresence_argparser = argparser.copy()
@api.route('/<string:community_uuid>/addpresence')
class AddPresence(Resource):
    addpresence_argparser.add_argument('location_uuid', type=str, required=True, location='form', help='Community node ID')
    addpresence_argparser.add_argument('relationship_property', type=str, required=False, location='form', help='Property of relationship')
    addpresence_argparser.add_argument('property_value', type=str, required=False, location='form', help='Value of proprety')
    # TODO: Allow a range of properties
    @api.expect(addpresence_argparser)
    @api.doc(responses={
        200: 'Success',
        400: 'Validation Error'
    })
    def put(self, community_uuid=None, location_uuid=None, relationship_property=None, property_value=None):
        '''Add location presence to community'''
        try:
            args = addpresence_argparser.parse_args()
            if args['location_uuid']:
                location_uuid = args['location_uuid']
            else:
                return '`location_uuid` is a required field', 400

            #Searching by uuid
            try:
                url = neo_http_ap + '/db/data/cypher'
                data = {'query': get_community_id_by_uuid, 'params': {'uuid': str(community_uuid)}}
                data = json.dumps(data, separators=(',', ':'))
                response = session.post(url, data=data, verify=False)
                if (response.ok):
                    community_id = response.json()['data'][0][0]  # Response gives what should be an int as a double array, needs to be 0 indexed twice to isolate
            except:
                message = 'Community could not be found\n'
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
                logger.debug(message)
                return message, 400

            relationship_type = 'has_presence_at'
            # Create new relationship
            url = neo_http_ap + '/db/data/node/' + str(community_id) + '/relationships'
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
                    return {'message': 'Location presence successfully added to community', 'response': str(response)}, 200
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


remove_presence_argparser = argparser.copy()
@api.route('/<string:community_uuid>/remove_presence')
class Remove_Presence(Resource):
    remove_presence_argparser.add_argument('location_uuid', type=str, required=True, location='form', help='Location node ID')
    @api.expect(remove_presence_argparser)
    @api.doc(responses={
        200: 'Success',
        400: 'Validation Error'
    })
    def delete(self, community_uuid=None, location_uuid=None,):
        '''Remove presence from location'''
        try:
            args = remove_presence_argparser.parse_args()
            if args['location_uuid']:
                location_uuid = args['location_uuid']
            else:
                return '`location_uuid` is a required field', 400
            url = neo_http_ap + '/db/data/cypher'
            try:
                data = {'query': get_has_presence_at, 'params': {'uuid1': str(community_uuid), 'uuid2':str(location_uuid)}}
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
                return 'Removed presence from location', 200

        except Exception as exc:
            message = 'Something went wrong'
            logger.critical(message)
            logger.dump_exception(exc)
            return message, 500


# TODO: UpdatePresence

# updaterelationship_argparser = argparser.copy()
# @api.route('/<string:id>/change')
# class UpdateRelationship(Resource):
#     updaterelationship_argparser.add_argument('id', type=str, required=True, location='form', help='Node ID')
#     updaterelationship_argparser.add_argument('property', type=str, required=True, location='form', help='Relationship property')
#     updaterelationship_argparser.add_argument('value', type=str, required=True, location='form', help='Property value')
#     @api.expect(updaterelationship_argparser)
#     @api.doc(responses={
#         200: 'Success',
#         400: 'Validation Error'
#     })
#     def put(self, id, property, value):
#         '''Update relationship'''
#         args = updaterelationship_argparser.parse_args()
#         if args['id']:
#             target_relationship_id = args['id']
#         else:
#             return '`id` is a required field', 400
#         if args['property']:
#             relationship_property = args['property']
#         else:
#             return '`property` is a required field', 400
#         if args['value']:
#             property_value = args['value']
#         else:
#             return '`property` is a required field', 400
#         url = neo_http_ap + '/db/data/relationship/' + str(target_relationship_id) + '/properties/' + str(relationship_property)
#         simple_log(url)
#         data = property_value
#         data = json.dumps(data, separators=(',',':'))
#         simple_log(data)
#         response = s.put(url, data=data, verify=False)
#         if (not response.ok):
#             try:
#                 problem = response.json()
#             except:
#                 problem = response
#             return ('Response to relationship property change not OK: %s' % str(problem)), 400
#         else:
#             return {'Relationship proprety change successful': str(response)}, 200

hostevent_argparser = argparser.copy()
@api.route('/<string:community_uuid>/hostevent')
class HostEvent(Resource):
    hostevent_argparser.add_argument('event_uuid', type=str, required=True, location='form',
                                         help='Event node ID')
    hostevent_argparser.add_argument('relationship_property', type=str, required=False, location='form',
                                         help='Property of relationship')
    hostevent_argparser.add_argument('property_value', type=str, required=False, location='form',
                                         help='Value of proprety')

    # TODO: Allow a range of properties
    @api.expect(hostevent_argparser)
    @api.doc(responses={
        200: 'Success',
        400: 'Validation Error'
    })
    def put(self, community_uuid=None, event_uuid=None, relationship_property=None, property_value=None):
        '''Community hosting event'''
        try:
            args = hostevent_argparser.parse_args()
            if args['event_uuid']:
                event_uuid = args['event_uuid']
            else:
                return '`event_uuid` is a required field', 400

            #Searching by uuid
            url = neo_http_ap + '/db/data/cypher'
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

            try:
                url = neo_http_ap + '/db/data/cypher'
                data = {'query': get_event_id_by_uuid, 'params': {'uuid': str(event_uuid)}}
                data = json.dumps(data, separators=(',', ':'))
                response = session.post(url, data=data, verify=False)
                if (response.ok):
                    event_id = response.json()['data'][0][0]  # Response gives what should be an int as a double array, needs to be 0 indexed twice to isolate
            except:
                message = 'Event could not be found\n'
                logger.debug(message)
                return message, 400

            relationship_type = 'hosting'
            # Create new relationship
            url = neo_http_ap + '/db/data/node/' + str(community_id) + '/relationships'
            data = {'to': neo_bolt_ap + '/db/data/node/' + str(event_id), 'type': relationship_type}
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
                return {'message': 'Successfully set Community hosting event',
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

unhost_event_argparser = argparser.copy()
@api.route('/<string:community_uuid>/unhost_event')
class Unhost_Event(Resource):
    unhost_event_argparser.add_argument('event_uuid', type=str, required=True, location='form', help='Event node ID')
    @api.expect(unhost_event_argparser)
    @api.doc(responses={
        200: 'Success',
        400: 'Validation Error'
    })
    def delete(self, community_uuid=None, event_uuid=None,):
        '''Remove presence from location'''
        try:
            args = unhost_event_argparser.parse_args()
            if args['event_uuid']:
                event_uuid = args['event_uuid']
            else:
                return '`event_uuid` is a required field', 400
            url = neo_http_ap + '/db/data/cypher'
            try:
                data = {'query': get_hosting, 'params': {'uuid1': str(community_uuid), 'uuid2':str(event_uuid)}}
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
                return 'Community unhosted event', 200

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
        '''Return a community's Image url'''
        try:
            args = read_argparser.parse_args()
            url = neo_http_ap + '/db/data/cypher'
            try:
                data = {'query': get_community_id_by_uuid, 'params': {'uuid': str(target_uuid)}}
                data = json.dumps(data, separators=(',', ':'))
                response = session.post(url, data=data, verify=False)
                if (response.ok):
                    target_id = response.json()['data'][0][0]
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
                return '/communities/'+str(filename),200
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

@api.route('/<string:target_uuid>/getmembercount')
class Read(Resource):
    @api.expect(read_argparser)
    @api.doc(responses={
        200: 'Success',
        400: 'Validation Error'
    })
    def get(self, target_uuid):
        '''Return the number of people in a community'''
        try:
            args = read_argparser.parse_args()
            url = neo_http_ap + '/db/data/cypher'
            try:
                data = {'query': get_community_count, 'params': {'uuid': str(target_uuid)}}
                data = json.dumps(data, separators=(',', ':'))
                response = session.post(url, data=data, verify=False)
                count = response.json()['data'][0][0]
            except:
                message = 'Product could not be found\n'
                logger.debug(message)
                return message, 400

            return count, 200
        except Exception as exc:
            message = 'Something went wrong'
            logger.critical(message)
            logger.dump_exception(exc)
            return message, 500

@api.route('/<string:target_uuid>/getmembers')
class Read(Resource):
    @api.expect(read_argparser)
    @api.doc(responses={
        200: 'Success',
        400: 'Validation Error'
    })
    def get(self, target_uuid):
        '''Return the people in a community'''
        try:
            args = read_argparser.parse_args()
            url = neo_http_ap + '/db/data/cypher'
            try:
                data = {'query': get_community_members, 'params': {'uuid': str(target_uuid)}}
                data = json.dumps(data, separators=(',', ':'))
                response = session.post(url, data=data, verify=False)
                members = response.json()['data'][0]
            except:
                message = 'Product could not be found'
                logger.debug(message)
                return message, 400

            members_data=[]
            for member in members:
                members_data.append(member['data'])

            return members_data, 200
        except Exception as exc:
            message = 'Something went wrong'
            logger.critical(message)
            logger.dump_exception(exc)
            return message, 500