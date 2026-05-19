from flask import request

from CTFd.models import Challenges
from CTFd.plugins.challenges import get_chal_class
from CTFd.plugins.LuaUtils import run_before_route
from CTFd.plugins.userchallenge.utils import userChallenge_allowed
from CTFd.utils import get_config
from CTFd.utils.user import authed


def load(app):
    
    def challengeAttempt():
        if authed() is False:
            return {"success": True, "data": {"status": "authentication_required"}}, 403

        if not request.is_json:
            request_data = request.form
        else:
            request_data = request.get_json()

        challenge_id = request_data.get("challenge_id")

        if get_config('allowUserChallenges'):
            non_admin = non_admin_preview(challenge_id)
            if(non_admin):
                return non_admin
        
    @userChallenge_allowed
    def non_admin_preview(challenge_id):
        preview = request.args.get("preview", False)
        if preview:
            challenge = Challenges.query.filter_by(id=challenge_id).first_or_404()
            chal_class = get_chal_class(challenge.type)
            status, message = chal_class.attempt(challenge, request)

            return {
                "success": True,
                "data": {
                    "status": "correct" if status else "incorrect",
                    "message": message,
                },
            }
        else:
            return False

    run_before_route(app,'api.challenges_challenge_attempt',challengeAttempt)