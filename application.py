import boto3
import datetime
import os
from time import clock

from botocore.client import Config
from flask import Flask, render_template, request, session, redirect, url_for
from flask_sqlalchemy import SQLAlchemy

# Variable Declarations
ACCESS_KEY_ID = 'access_key'
ACCESS_SECRET_KEY = 'access_secret'
BUCKET_NAME = 'imagegenerator-images'
IMAGES_ROOT_PATH = 'https://s3.amazonaws.com/imagegenerator-images/'
APP_ROOT = os.path.dirname(os.path.abspath(__file__))

# App Config
application = Flask(__name__)
application.secret_key = 'Secret'
application.config[
    'SQLALCHEMY_DATABASE_URI'] = 'db'
application.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# S3 Connection
s3 = boto3.resource('s3',
                    aws_access_key_id=ACCESS_KEY_ID,
                    aws_secret_access_key=ACCESS_SECRET_KEY,
                    config=Config(signature_version='s3v4'))
s3client = boto3.client('s3',
                        aws_access_key_id=ACCESS_KEY_ID,
                        aws_secret_access_key=ACCESS_SECRET_KEY)
# DB Connection
db = SQLAlchemy(application)


class Images(db.Model):
    __tablename__ = 'images'
    owner = db.Column('owner', db.Unicode, primary_key='false')
    created = db.Column('created', db.DateTime)
    title = db.Column('title', db.Unicode, primary_key='true')
    image_location = db.Column('image_location', db.Unicode)
    modified = db.Column('modified', db.DateTime)
    likes = db.Column('likes', db.Integer)
    rating = db.Column('rating', db.Integer)
    number_of_ratings = db.Column('number_of_ratings', db.Integer)

    def __init__(self, owner, title, image_location, created, modified, likes, rating, number_of_ratings):
        self.owner = owner
        self.title = title
        self.image_location = image_location
        self.created = created
        self.modified = modified
        self.likes = likes
        self.rating = rating
        self.number_of_ratings = number_of_ratings


@application.route('/')
def index():
    if 'username' in session:
        username = session['username']
        return redirect(url_for('view'))
    return render_template('login.html')


@application.route('/logout')
def logout():
    session.pop('username', None)
    session.pop('mode', None)
    return render_template('login.html')


@application.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        session['username'] = request.form['username']
        session['mode'] = request.form['vieworcreate']
        return redirect(url_for('view'))


@application.route('/upload', methods=['GET', 'POST'])
def upload():
    username = session['username']
    title = request.form['image_title']
    title_path = title + '.jpg'
    title_exists = Images.query.filter_by(title=title).first()
    utc_now = datetime.datetime.utcnow()
    if title_exists is None:
        new_image = Images(username, title, title_path, utc_now, utc_now, 0, 0, 0)
        db.session.add(new_image)
    else:
        title_exists.modified = utc_now
    db.session.commit()
    s3.Bucket(BUCKET_NAME).put_object(Key=title_path, Body=request.files['file_upload'])
    session['mode'] = 'view'
    return redirect(url_for('properties', title=title))


@application.route('/search', methods=['GET', 'POST'])
def search():
    username = session['username']
    title = request.form['image_title']
    title_exists = Images.query.filter_by(title=title).first()
    if title_exists is None:
        return '<head>' \
               '<link rel="stylesheet" href="https://maxcdn.bootstrapcdn.com/bootstrap/3.3.7/css/bootstrap.min.css"> ' \
               '</head>'\
               '<body>'\
               '<h1 class="text-danger">The Image you are searching for does not exist.<br/> '  \
                'Please search for an image with a different Title </h1> ' \
               ' <a href=' + url_for("search_image") + '>Click Here to Go Back</a></body>'
    else:
        return redirect(url_for('properties', title=title))


@application.route('/search_image')
def search_image():
    username = session['username']
    return render_template('search.html', username=username)


@application.route('/edit/<title>', methods=['GET', 'POST'])
def edit(title):
    new_title = request.form['image_title']
    title_exists = Images.query.filter_by(title=new_title).first()
    if title_exists is None:
        title_exists = Images.query.filter_by(title=title).first()
        title_exists.title = new_title
        title_exists.image_location = new_title + '.jpg'
        db.session.commit()
        return redirect(url_for('properties', title=new_title))
    else:
        return '<head>' \
               '<link rel="stylesheet" href="https://maxcdn.bootstrapcdn.com/bootstrap/3.3.7/css/bootstrap.min.css"> ' \
               '</head>'\
               '<body>'\
               '<h1 class="text-danger">The Title already exists, Please choose another title. </h1> ' \
               ' <a href='+url_for("properties",title=title)+'>Click Here to Go Back</a></body>'


@application.route('/like/<title>', methods=['GET', 'POST'])
def like(title):
    referrer = request.referrer
    title_exists = Images.query.filter_by(title=title).first()
    current_likes = title_exists.likes
    title_exists.likes=current_likes + 1
    db.session.commit()
    if 'view_images' in referrer:
        return redirect(url_for('view',title=title))
    return redirect(url_for('properties', title=title))


@application.route('/rate/<title>', methods=['GET', 'POST'])
def rate(title):
    print("Inside Route")
    referrer = request.referrer
    title_exists = Images.query.filter_by(title=title).first()
    current_rating = title_exists.rating
    current_number_of_ratings = title_exists.number_of_ratings
    new_rating = request.form['ratingValue']
    if current_rating==0:
        rating = new_rating
    else:
        rating = int(round((current_rating + int(new_rating))/2))
    title_exists.rating = rating
    title_exists.number_of_ratings = current_number_of_ratings + 1
    db.session.commit()
    if 'view_images' in referrer:
        return redirect(url_for('view',title=title))
    return redirect(url_for('properties', title=title))


@application.route('/properties/<title>', methods=['GET', 'POST'])
def properties(title):
    username = session['username']
    time = clock()
    title_exists = Images.query.filter_by(title=title).first()
    owner = title_exists.owner
    title = title_exists.title
    created = title_exists.created
    image_full_path = IMAGES_ROOT_PATH + title_exists.image_location + '?' + str(clock())
    modified = title_exists.modified
    likes = title_exists.likes
    rating = title_exists.rating

    return render_template('properties.html', username=username, owner=owner, title=title, \
                           created=created, image_full_path=image_full_path, \
                           modified=modified, likes=likes,rating=rating)


@application.route('/view', methods=['GET', 'POST'])
def view():
    if 'username' in session:
        username = session['username']
        mode = session['mode']
        if mode == 'view':
            return redirect(url_for('view_images'))
        else:
            return redirect(url_for('upload_images'))
    return redirect(url_for('login'))


@application.route('/view_images')
def view_images():
    username = session['username']
    images = Images.query.all()
    time = clock()
    return render_template('view.html', username=username,images=images, images_root_path=IMAGES_ROOT_PATH,utc_now=str(time))


@application.route('/upload_images')
def upload_images():
    username = session['username']
    return render_template('upload.html', username=username)


@application.route('/delete/<title>')
def delete(title):
    s3client.delete_object(Bucket=BUCKET_NAME, Key=title)
    delete_object = Images.query.filter_by(title=title).first()
    db.session.delete(delete_object)
    db.session.commit()
    return redirect(url_for('view_images'))


if __name__ == '__main__':
    application.run(debug=True)
