import functools

from flask import request

from CTFd.models import Challenges
from CTFd.plugins.challenges import get_chal_class
from CTFd.plugins.userchallenge.utils import user_owns_challenge
from CTFd.utils import get_config
from CTFd.utils.user import authed


def load(app):
    def owner_preview_attempt():
        """
        Lets the creator of a user challenge test flags from the preview page
        (?preview=true) without the attempt being recorded and even while the
        challenge is hidden. Returns None for every other request.
        """
        if not request.args.get("preview", False):
            return None
        if not get_config("allowUserChallenges") or not authed():
            return None

        if not request.is_json:
            request_data = request.form
        else:
            request_data = request.get_json(silent=True) or {}
        challenge_id = request_data.get("challenge_id")

        if not user_owns_challenge(challenge_id):
            return None

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

    endpoint = "api.challenges_challenge_attempt"
    original = app.view_functions[endpoint]

    # Wrap the view directly (instead of LuaUtils.run_before_route, which always
    # runs the core view as well) so an owner preview never reaches the core
    # attempt logic: no submission is recorded and hidden challenges work.
    @functools.wraps(original)
    def attempt_with_owner_preview(*args, **kwargs):
        preview = owner_preview_attempt()
        if preview is not None:
            return preview
        return original(*args, **kwargs)

    app.view_functions[endpoint] = attempt_with_owner_preview
