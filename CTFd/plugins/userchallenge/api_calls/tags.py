

from flask import request

from CTFd.models import Tags, db
from CTFd.plugins.userchallenge.utils import (
    ReadOnly,
    challenge_id_from,
    require_body_challenge_owner,
    require_challenge_owner,
    userChallenge_allowed,
)
from CTFd.schemas.tags import TagSchema


def load(app):
    @app.route('/userchallenge/api/tags', methods=['GET'])
    @userChallenge_allowed
    def getAvailableTags():
        tags = (
            Tags.query.with_entities(Tags.value)
            .filter(Tags.value.isnot(None))
            .distinct()
            .order_by(Tags.value)
            .all()
        )

        return {"success": True, "data": [{"value": tag.value} for tag in tags]}

    @app.route('/userchallenge/api/challenges/<challenge_id>/tags',methods=['GET'])
    @userChallenge_allowed
    def getChallengeTags(challenge_id):
        require_challenge_owner(challenge_id)
        response = []

        tags = Tags.query.filter_by(challenge_id=challenge_id).all()

        for t in tags:
            response.append(
                {"id": t.id, "challenge_id": t.challenge_id, "value": t.value}
            )
        return {"success": True, "data": response}

    @app.route('/userchallenge/api/tags',methods=['POST'])
    @userChallenge_allowed
    @ReadOnly
    def createTag():
        req = request.get_json()
        require_challenge_owner(challenge_id_from(req))
        schema = TagSchema()
        response = schema.load(req, session=db.session)

        if response.errors:
            return {"success": False, "errors": response.errors}, 400

        db.session.add(response.data)
        db.session.commit()

        response = schema.dump(response.data)
        db.session.close()

        return {"success": True, "data": response.data}
    @app.route('/userchallenge/api/tags/<tag_id>',methods=['GET'])
    @userChallenge_allowed
    def getTag(tag_id):
        tag = Tags.query.filter_by(id=tag_id).first_or_404()
        require_challenge_owner(tag.challenge_id)

        response = TagSchema().dump(tag)

        if response.errors:
            return {"success": False, "errors": response.errors}, 400

        return {"success": True, "data": response.data}
    @app.route('/userchallenge/api/tags/<tag_id>',methods=['PATCH'])
    @userChallenge_allowed
    @ReadOnly
    def patchTag(tag_id):
        tag = Tags.query.filter_by(id=tag_id).first_or_404()
        require_challenge_owner(tag.challenge_id)
        schema = TagSchema()
        req = request.get_json()
        require_body_challenge_owner(req)

        response = schema.load(req, session=db.session, instance=tag)
        if response.errors:
            return {"success": False, "errors": response.errors}, 400

        db.session.commit()

        response = schema.dump(response.data)
        db.session.close()

        return {"success": True, "data": response.data}
    @app.route('/userchallenge/api/tags/<tag_id>',methods=['DELETE'])
    @userChallenge_allowed
    @ReadOnly
    def deleteTag(tag_id):
        tag = Tags.query.filter_by(id=tag_id).first_or_404()
        require_challenge_owner(tag.challenge_id)
        db.session.delete(tag)
        db.session.commit()
        db.session.close()

        return {"success": True}
