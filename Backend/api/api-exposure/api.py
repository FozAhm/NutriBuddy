from flask import Flask, render_template
from flask_restplus import Resource, Api
from flask_cors import CORS, cross_origin
#from apis import blueprint as api
from exposure import blueprint as api

app = Flask(__name__)
CORS(app)
app.register_blueprint(api)

if __name__ == '__main__':
	app.run(host='0.0.0.0', debug=True, port=5000)