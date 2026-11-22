

from flask import request

from CTFd.models import Hints, db
from CTFd.plugins.userchallenge.utils import (
    ReadOnly,
    challenge_id_from,
    require_body_challenge_owner,
    require_challenge_owner,
    userChallenge_allowed,
)
from CTFd.schemas.hints import HintSchema


def load(app):
    @app.route('/userchallenge/api/challenges/<challenge_id>/hints',methods=['GET'])
    @userChallenge_allowed
    def getHints(challenge_id):
        require_challenge_owner(challenge_id)
        hints = Hints.query.filter_by(challenge_id=challenge_id).all()
        schema = HintSchema(many=True)
        response = schema.dump(hints)

        if response.errors:
            return {"success": False, "errors": response.errors}, 400

        return {"success": True, "data": response.data}
    @app.route('/userchallenge/api/hints',methods=['POST'])
    @userChallenge_allowed
    @ReadOnly
    def createHint():
        req = request.get_json()
        require_challenge_owner(challenge_id_from(req))
        schema = HintSchema(view="admin")
        response = schema.load(req, session=db.session)

        if response.errors:
            return {"success": False, "errors": response.errors}, 400

        db.session.add(response.data)
        db.session.commit()

        response = schema.dump(response.data)

        return {"success": True, "data": response.data}
    @app.route('/userchallenge/api/hints/<hint_id>',methods=['GET'])
    @userChallenge_allowed
    def getHint(hint_id):
        hint = Hints.query.filter_by(id=hint_id).first_or_404()
        # Only the challenge's creator (or an admin) may read hints through this
        # API, so they always get the full admin view of their own hint
        require_challenge_owner(hint.challenge_id)

        response = HintSchema(view="admin").dump(hint)

        if response.errors:
            return {"success": False, "errors": response.errors}, 400

        return {"success": True, "data": response.data}
    @app.route('/userchallenge/api/hints/<hint_id>',methods=['PATCH'])
    @ReadOnly
    @userChallenge_allowed
    def patchHint(hint_id):
        hint = Hints.query.filter_by(id=hint_id).first_or_404()
        require_challenge_owner(hint.challenge_id)
        req = request.get_json()
        require_body_challenge_owner(req)

        schema = HintSchema(view="admin")
        response = schema.load(req, instance=hint, partial=True, session=db.session)

        if response.errors:
            return {"success": False, "errors": response.errors}, 400

        db.session.add(response.data)
        db.session.commit()

        response = schema.dump(response.data)

        return {"success": True, "data": response.data}
    @app.route('/userchallenge/api/hints/<hint_id>',methods=['DELETE'])
    @userChallenge_allowed
    @ReadOnly
    def deleteHint(hint_id):
        hint = Hints.query.filter_by(id=hint_id).first_or_404()
        require_challenge_owner(hint.challenge_id)
        db.session.delete(hint)
        db.session.commit()
        db.session.close()

        return {"success": True}
