import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy

basedir = os.path.abspath(os.path.dirname(__file__))

db = SQLAlchemy()


def create_app():
    app = Flask(__name__, static_folder="static", template_folder="templates")

    root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(root, 'datasets.db')
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['UPLOAD_FOLDER'] = os.path.join(root, 'uploads')
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

    db.init_app(app)

    with app.app_context():
        # import routes and models so they are registered
        from . import models  # noqa: F401
        from . import routes  # noqa: F401
        db.create_all()

    return app
