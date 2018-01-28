from flask_restplus import Api

from nodes.image_processing import api as image_processing

from flask import Blueprint

blueprint = Blueprint('Node Managers', __name__)
api = Api(blueprint)

api.add_namespace(image_processing, path='/image_processing')
