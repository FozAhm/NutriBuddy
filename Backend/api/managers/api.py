from flask import Flask, render_template, url_for, send_from_directory, request, redirect
from flask_restplus import Resource, Api
from flask_cors import CORS, cross_origin
#from apis import blueprint as api
from werkzeug.utils import secure_filename
from nodes import blueprint as api
import os

UPLOAD_FOLDER = '/Users/Coeurl/Documents/Xcode'
ALLOWED_EXTENSIONS = set(['jpg'])

app = Flask(__name__)
CORS(app)
app.register_blueprint(api)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1] in ALLOWED_EXTENSIONS

#return image
@app.route('/image/<path:path>')
def send_image(path):
	directory = os.path.dirname(os.path.realpath(__file__)) +'/nodes/static/'
	print("Fetching from: " + directory + path)
	return send_from_directory(directory,path)

@app.route("/imageupload", methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        file = request.files['file']
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            return redirect(url_for('index'))
    return """
    <!doctype html>
    <title>Upload new File</title>
    <h1>Upload new File</h1>
    <form action="" method=post enctype=multipart/form-data>
      <p><input type=file name=file>
         <input type=submit value=Upload>
    </form>
    <p>%s</p>
    """ % "<br>".join(os.listdir(app.config['UPLOAD_FOLDER'],))


if __name__ == '__main__':
	app.run(host='0.0.0.0', debug=True, port=5001)