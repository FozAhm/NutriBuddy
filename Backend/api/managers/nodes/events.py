# ======================================================
# ======================================================
# EVENTS
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

logger = SimpleLogger('EventsManager', 5)

# orchestrator= os.getenv('Orchestrator_AP' ,'0.0.0.0:5000')
# mongoIP=os.getenv('CMDB_AP' ,'0.0.0.0:27017')
# client = MongoClient(mongoIP.split(":")[0], int(mongoIP.split(":")[1]) , connect=False)
# #client = MongoClient("mongodb://mongodb0.example.net:27017")
# db = client.client

api = Namespace('events', description='Neo4j event-related operations')

events = api.model('events', {
    'type': fields.String(description='The resource identifier'),
})

events_container = api.model('consumersContainer', {
    'events': fields.Nested(events),
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
    create_argparser.add_argument('name', type=str, required=True, location='form', help='Event name')
    create_argparser.add_argument('date', type=str, required=True, location='form', help='Format yyyy-mm-dd hour:minute')
    # TODO: Allow other properties
    @api.expect(create_argparser)
    @api.doc(responses={
        200: 'Success',
        400: 'Validation Error'
    })
    def post(self, name=None):
        '''Add an event'''
        try:
            args = create_argparser.parse_args()
            if args['name']:
                name = args['name']
            else:
                return '`name` is a required field', 400
            if args['date']:
                date = datetime.datetime.strptime(args['date'], "%Y-%m-%d %H:%M")
            else:
                return '`date` is a required field', 400
            label = 'Event'
            # Create new node
            url = neo_http_ap + '/db/data/node'
            data = {
                    'name': name,
                    'date': str(date),
                    'uuid': str(uuid.uuid4())
                    }
            data = json.dumps(data, separators=(',',':'))
            response = session.post(url, data=data, headers=headers, verify=False)
            if (response.ok):
                logger.debug('Successfully created event: ' + str(response))
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
        '''Get a event by UUID'''
        try:
            args = read_argparser.parse_args()
            url = neo_http_ap + '/db/data/cypher'
            try:
                data = {'query': get_event_id_by_uuid, 'params': {'uuid': str(target_uuid)}}
                data = json.dumps(data, separators=(',', ':'))
                response = session.post(url, data=data, verify=False)
                if (response.ok):
                    target_id = response.json()['data'][0][0]  # Response gives what should be an int as a double array, needs to be 0 indexed twice to isolate
            except:
                message = 'Event could not be found\n'
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
        '''Get 1000 events'''
        try:
            url = neo_http_ap + '/db/data/label/Event/nodes'
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
        '''Update event node, empty value will delete property'''
        try:
            args = update_argparser.parse_args()
            if args['property']:
                property = args['property']
            else:
                return '`property` is a required field', 400
            url = neo_http_ap + '/db/data/cypher'
            try:
                data = {'query': get_event_id_by_uuid, 'params': {'uuid': str(target_uuid)}}
                data = json.dumps(data, separators=(',', ':'))
                response = session.post(url, data=data, verify=False)
                if (response.ok):
                    target_id = response.json()['data'][0][0]  # Response gives what should be an int as a double array, needs to be 0 indexed twice to isolate
            except:
                message = 'Event could not be found\n'
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
                message = 'Response to event properties retrieval not OK:\n%s' % response_dump
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
                    return {'message': 'Event successfully updated', 'response': str(response)}, 200
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
        '''Delete a Event by UUID'''
        try:
            # Get and delete all relationships of node first
            #Get node id
            url = neo_http_ap + '/db/data/cypher'
            try:
                data = {'query': get_event_id_by_uuid, 'params': {'uuid': str(target_uuid)}}
                data = json.dumps(data, separators=(',', ':'))
                response = session.post(url, data=data, verify=False)
                if (response.ok):
                    target_id = response.json()['data'][0][0]  # Response gives what should be an int as a double array, needs to be 0 indexed twice to isolate
            except:
                message = 'Event could not be found\n'
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
                return {'message': 'Event deletion was successful', 'response': str(response)}, 200
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

setlocation_argparser = argparser.copy()
@api.route('/<string:event_uuid>/setlocation')
class SetLocation(Resource):
    setlocation_argparser.add_argument('location_uuid', type=str, required=True, location='form',
                                         help='Location node ID')
    setlocation_argparser.add_argument('relationship_property', type=str, required=False, location='form',
                                         help='Property of relationship')
    setlocation_argparser.add_argument('property_value', type=str, required=False, location='form',
                                         help='Value of proprety')

    # TODO: Allow a range of properties
    @api.expect(setlocation_argparser)
    @api.doc(responses={
        200: 'Success',
        400: 'Validation Error'
    })
    def put(self, event_uuid=None, location_uuid=None, relationship_property=None, property_value=None):
        '''Set location of an event'''
        try:
            args = setlocation_argparser.parse_args()
            if args['location_uuid']:
                location_uuid = args['location_uuid']
            else:
                return '`location_uuid` is a required field', 400
            # Searching by uuid
            url = neo_http_ap + '/db/data/cypher'
            try:
                data = {'query': get_event_id_by_uuid, 'params': {'uuid': str(event_uuid)}}
                data = json.dumps(data, separators=(',', ':'))
                response = session.post(url, data=data, verify=False)
                print(response)
                if (response.ok):
                    event_id = response.json()['data'][0][0]  # Response gives what should be an int as a double array, needs to be 0 indexed twice to isolate
            except:
                message = 'Event could not be found\n'
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
            relationship_type = 'happening_at'
            # Create new relationship
            url = neo_http_ap + '/db/data/node/' + str(event_id) + '/relationships'
            data = {'to': neo_bolt_ap + '/db/data/node/' + str(location_id), 'type': relationship_type}
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
                return {'message': 'Location successfuly set for event',
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

remove_location_argparser = argparser.copy()
@api.route('/<string:event_uuid>/remove_location')
class Remove_Location(Resource):
    remove_location_argparser.add_argument('location_uuid', type=str, required=True, location='form', help='Location node ID')
    @api.expect(remove_location_argparser)
    @api.doc(responses={
        200: 'Success',
        400: 'Validation Error'
    })
    def delete(self, event_uuid=None, location_uuid=None,):
        '''Remove presence from location'''
        try:
            args = remove_location_argparser.parse_args()
            if args['location_uuid']:
                location_uuid = args['location_uuid']
            else:
                return '`location_uuid` is a required field', 400
            url = neo_http_ap + '/db/data/cypher'
            try:
                data = {'query': get_happening_at, 'params': {'uuid1': str(event_uuid), 'uuid2':str(location_uuid)}}
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
                return 'Removed location from event', 200

        except Exception as exc:
            message = 'Something went wrong'
            logger.critical(message)
            logger.dump_exception(exc)
            return message, 500


#TODO: CHANGELOCATION
