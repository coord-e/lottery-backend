import random
from flask import Blueprint, jsonify, request, g
from api.models import Lottery, Classroom, User, Application, db
from api.schemas import (
    user_schema,
    classrooms_schema,
    classroom_schema,
    application_schema,
    lotteries_schema,
    lottery_schema
)
from api.auth import login_required
from api.swagger import spec

bp = Blueprint(__name__, 'api')


@bp.route('/classrooms')
@spec('api/classrooms.yml')
def list_classrooms():
    """
        return classroom list
    """
# those two values will be used in the future. now, not used. see issue #59 #60
#     filter = request.args.get('filter')
#     sort = request.args.get('sort')

    classrooms = Classroom.query.all()
    result = classrooms_schema.dump(classrooms)[0]
    return jsonify(result)


@bp.route('/classrooms/<int:idx>')
@spec('api/classrooms/idx.yml')
def list_classroom(idx):
    """
        return infomation about specified classroom
    """
    classroom = Classroom.query.get(idx)
    if classroom is None:
        return jsonify({"message": "Classroom could not be found."}), 404
    result = classroom_schema.dump(classroom)[0]
    return jsonify(result)


@bp.route('/lotteries')
@spec('api/lotteries.yml')
def list_lotteries():
    """
        return lotteries list.
    """
# those two values will be used in the future. now, not used. see issue #62 #63
#     filter = request.args.get('filter')
#     sort = request.args.get('sort')

    lotteries = Lottery.query.all()
    result = lotteries_schema.dump(lotteries)[0]
    return jsonify(result)


@bp.route('/lotteries/<int:idx>', methods=['GET'])
@spec('api/lotteries/idx.yml')
def list_lottery(idx):
    """
        return infomation about specified lottery.
    """
    lottery = Lottery.query.get(idx)
    if lottery is None:
        return jsonify({"message": "Lottery could not be found."}), 404
    result = lottery_schema.dump(lottery)[0]
    return jsonify(result)


@bp.route('/lotteries/<int:idx>', methods=['POST', 'DELETE'])
@spec('api/lotteries/apply.yml', methods=['POST'])
@spec('api/lotteries/cancel.yml', methods=['DELETE'])
@login_required()
def apply_lottery(idx):
    """
        apply/cancel applications.
        specify the lottery id in the URL.
    """
    lottery = Lottery.query.get(idx)
    if lottery is None:
        return jsonify({"message": "Lottery could not be found."}), 404
    if lottery.done:
        return jsonify({"message": "This lottery has already done"}), 400
    user = User.query.filter_by(id=g.token_data['user_id']).first()
    previous = Application.query.filter_by(user_id=user.id)
    if any(app.lottery.index == lottery.index and
            app.lottery.id != lottery.id
            for app in previous.all()):
        msg = "You're already applying to a lottery in this period"
        return jsonify({"message": msg}), 400
    application = previous.filter_by(lottery_id=lottery.id).first()
    # access DB
    if request.method == 'POST':
        if not application:
            newapplication = Application(
                lottery_id=lottery.id, user_id=user.id, status="pending")
            db.session.add(newapplication)
            db.session.commit()
            result = application_schema.dump(newapplication)[0]
            return jsonify(result)
        else:
            result = application_schema.dump(application)[0]
            return jsonify(result)
    else:
        if application:
            db.session.delete(application)
            db.session.commit()
            return jsonify({"message": "Successful Operation"})
        else:
            return jsonify({"message":
                            "You're not applying for this lottery"}), 400


@bp.route('/lotteries/<int:idx>/draw', methods=['POST'])
@spec('api/lotteries/draw.yml')
@login_required('admin')
def draw_lottery(idx):
    """
        draw lottery as adminstrator
    """
    lottery = Lottery.query.get(idx)
    if lottery is None:
        return jsonify({"message": "Lottery could not be found."}), 404
    if lottery.done:
        return jsonify({"message": "This lottery is already done "
                        "and cannot be undone"}), 400
    applications = Application.query.filter_by(lottery_id=idx).all()
    if len(applications) == 0:
        return jsonify({"message": "Nobody is applying to this lottery"}), 400
    chosen = random.choice(applications)
    for application in applications:
        application.status = "won" if application.id == chosen.id else application.status = "lose"
        db.session.add(application)

    lottery.done = True
    db.session.commit()
    winner = User.query.get(chosen.user_id)
    result = user_schema.dump(winner)
    return jsonify(result)


@bp.route('/status', methods=['GET'])
@spec('api/status.yml')
@login_required()
def get_status():
    """
        return user's id and applications
    """
    user = User.query.filter_by(id=g.token_data['user_id']).first()
    result = user_schema.dump(user)[0]
    return jsonify(result)
