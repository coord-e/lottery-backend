from flask import Flask, current_app
from flask_cors import CORS
import sqlalchemy
from .routes import auth, api
from .swagger import swag
from .models import db
from cards.id import load_id_json_file, decode_public_id
import os
import sys

config = {
    "development": "api.config.DevelopmentConfig",
    "testing": "api.config.TestingConfig",
    "preview": "api.config.PreviewDeploymentConfig",
    "deployment": "api.config.DeploymentConfig",
    "default": "api.config.DevelopmentConfig"
}


def create_app():
    """create base flask application
        1. generate flask application
        2. set config based on 'FLASK_CONFIGURATION'
        3. initialize DB
        4. some other settings

        Args:
            no-args needed

        ENVIRONMENT_VALIABLES:
            FLASK_CONFIGURATION (str): define config type.
                ('defalut'|'development'|'testing'|'preview'|'deployment')
        Return:
            app (Flask): generated flask application
        Exit Status:
            4 : SQLALCHEMY_DATABASE_URI or SECRET_KEY is not set.

    """
    app = Flask(__name__, instance_relative_config=True)

    # Allow to access with or without trailing slash
    app.url_map.strict_slashes = False

    CORS(app, supports_credentials=True)

    # load app sepcified configuration
    config_name = os.getenv('FLASK_CONFIGURATION', 'default')

    app.config.from_object(config[config_name])
    app.config.from_pyfile('config.cfg', silent=True)

    if app.config.get('SQLALCHEMY_DATABASE_URI', None) is None:
        app.logger.error(
            "SQLALCHEMY_DATABASE_URI is not set."
            "Didn't you forget to set it in instance/config.cfg?")
        sys.exit(4)  # Return 4 to exit gunicorn

    if app.config.get('SECRET_KEY', None) is None:
        app.logger.error(
            "SECRET_KEY is not set."
            "Didn't you forget to set it in instance/config.cfg?")
        sys.exit(4)  # Return 4 to exit gunicorn

    db.init_app(app)
    swag.init_app(app)

    app.register_blueprint(auth.bp)
    app.register_blueprint(api.bp)

    with app.app_context():
        if sqlalchemy.inspect(db.engine).get_table_names() == []:
            app.logger.warning(
                'Generating Initial Data for Database in the first run')
            db.create_all()
            generate()

    return app


def initdb(app, db):
    from api.models import db
    db.create_all()


def generate():
    """generate DB contents
        1. generate classrooms
        2. generate lotteries
        3. generate users

        Args:
            no-args needed
        Return:
            no-return given
    """
    from .models import Lottery, Classroom, User, db
    total_index = 4
    grades = [5, 6]

    def classloop(f):
        for grade in grades:
            for class_index in range(4):  # 0->A 1->B 2->C 3->D
                f(grade, class_index)

    def create_classrooms(grade, class_index):
        room = Classroom(grade=grade, index=class_index)
        db.session.add(room)

    def create_lotteries(grade, class_index):
        room = Classroom.query.filter_by(
            grade=grade, index=class_index).first()
        for perf_index in range(total_index):
            lottery = Lottery(classroom_id=room.id,
                              index=perf_index, done=False)
            db.session.add(lottery)

    classloop(create_classrooms)
    db.session.commit()
    classloop(create_lotteries)
    db.session.commit()

    json_path = current_app.config['ID_LIST_FILE']
    id_list = load_id_json_file(json_path)
    for ids in id_list:
        user = User(secret_id=ids['secret_id'],
                    public_id=decode_public_id(ids['public_id']),
                    authority=ids['authority'])
        db.session.add(user)

    db.session.commit()
