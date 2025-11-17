import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy

basedir = os.path.abspath(os.path.dirname(__file__))

db = SQLAlchemy()


def create_app():
    app = Flask(__name__, static_folder="static", template_folder="templates")

    root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    
    # Use /tmp directory for Vercel serverless environment
    is_vercel = os.environ.get('VERCEL', False)
    is_render = os.environ.get('RENDER', False)
    
    if is_vercel:
        db_path = '/tmp/datasets.db'
        upload_path = '/tmp/uploads'
    elif is_render:
        # Render provides persistent disk at /opt/render/project/src
        db_path = os.path.join(root, 'datasets.db')
        upload_path = os.path.join(root, 'uploads')
    else:
        db_path = os.path.join(root, 'datasets.db')
        upload_path = os.path.join(root, 'uploads')
    
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + db_path
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['UPLOAD_FOLDER'] = upload_path
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

    db.init_app(app)

    with app.app_context():
        # import routes and models so they are registered
        from . import models  # noqa: F401
        from . import routes  # noqa: F401
        db.create_all()

    return app
