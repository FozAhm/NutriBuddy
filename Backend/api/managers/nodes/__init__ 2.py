from flask_restplus import Api

from nodes.consumers import api as consumers
from nodes.communities import api as communities
from nodes.locations import api as locations
from nodes.products import api as products
from nodes.organizations import api as organizations
from nodes.events import api as events
from nodes.purchases import api as purchases
from nodes.raincheck import api as rainchecks
from nodes.receipt import api as receipts
from nodes.employees import api as employees
from nodes.deal import api as deals

from flask import Blueprint

blueprint = Blueprint('Node Managers', __name__)
api = Api(blueprint)

api.add_namespace(consumers, path='/consumers')
api.add_namespace(communities, path='/communities')
api.add_namespace(events, path='/events')
api.add_namespace(locations, path='/locations')
api.add_namespace(products, path='/products')
api.add_namespace(organizations, path='/organizations')
api.add_namespace(purchases, path='/purchases')
api.add_namespace(rainchecks, path='/rainchecks')
api.add_namespace(receipts, path ='/receipts')
api.add_namespace(employees, path = '/employees')
api.add_namespace(deals, path = '/deals')