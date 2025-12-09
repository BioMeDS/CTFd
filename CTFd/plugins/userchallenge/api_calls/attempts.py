from CTFd.cache import clear_challenges, clear_standings
from CTFd.models import Challenges, Fails, Solves
from CTFd.plugins.challenges import get_chal_class
from CTFd.plugins.LuaUtils import run_before_route
from CTFd.plugins.userchallenge.utils import userChallenge_allowed
from CTFd.utils import config, get_config
from CTFd.utils import user as current_user
from CTFd.utils.dates import ctf_paused, ctftime
from CTFd.utils.decorators import during_ctf_time_only, require_verified_emails
from CTFd.utils.decorators.visibility import check_challenge_visibility
from CTFd.utils.humanize.words import pluralize
from CTFd.utils.logging import log
from CTFd.utils.user import authed, get_current_team, get_current_user
from flask import abort, request


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