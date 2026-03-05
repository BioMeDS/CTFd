from flask import Blueprint, abort, render_template, request, url_for

from CTFd.models import Challenges, Configs, Flags, Solves, db
from CTFd.plugins.challenges import CHALLENGE_CLASSES, get_chal_class
from CTFd.plugins.LuaUtils import (
    ConfigPanel,
    _LuaAsset,
    merge_text,
    run_after_route,
    run_before_route,
    toggle_config,
)
from CTFd.plugins.userchallenge.api_calls import (
    attempts,
    challenges,
    comments,
    files,
    flags,
    hints,
    tags,
    topics,
)
from CTFd.plugins.userchallenge.utils import *
from CTFd.utils import config
from CTFd.utils.decorators import admins_only, authed_only
from CTFd.utils.helpers import get_errors, get_infos
from CTFd.utils.logging import log

userChallenge = Blueprint(
    "userchallenge", __name__, template_folder="templates", static_folder="staticAssets"
)


def load(app):
    app.db.create_all()
    app.jinja_env.globals.update(UserChallengeAsset=_LuaAsset("userchallenge"))
    app.jinja_env.globals.update(UserChallengeReadOnly=isReadOnly)
    app.jinja_env.globals.update(UserChallengeShowLink=showLink)

    app.register_blueprint(userChallenge, url_prefix="/userchallenge")

    # add config value false for allowing user challenges if not existent on startup
    if not Configs.query.filter_by(key="allowUserChallenges").first():
        conf = Configs(key="allowUserChallenges", value="false")
        db.session.add(conf)
        db.session.commit()

    @authed_only
    def Challenge_user(res):
        infos = get_infos()
        errors = get_errors()

        user = get_current_user()

        if config.is_scoreboard_frozen():
            infos.append("Scoreboard has been frozen")

        return merge_text(
            res[0],
            render_template(
                "newUserPage.html",
                user=user,
                account=user.account,
                infos=infos,
                errors=errors,
            ),
        )

    run_after_route(app, "users.private", Challenge_user)

    # config page admins
    @app.route("/admin/userChallenge")
    @admins_only
    def user_config():
        allow = get_config("allowUserChallenges")
        readonly = get_config("isReadOnlyUserChallenges")

        if allow:
            allow = "enabled"
        else:
            allow = "disabled"

        if readonly:
            readonly = "enabled"
        else:
            readonly = "disabled"

        configs = []
        configs.append(
            ConfigPanel(
                "User-Challenges",
                "Enableing User-Challenges gives all users access to create and edit their own challenges.",
                allow,
                "allowUserChallenges",
            )
        )
        configs.append(
            ConfigPanel(
                "Read Only",
                "If enabled, every User who created challenges can still view them but not edit them.",
                readonly,
                "isReadOnlyUserChallenges",
            )
        )

        return render_template("notificationConfig.html", configs=configs)

    # add creation date and user to listing
    @admins_only
    def challenges_listing(res):

        
        q = request.args.get("q")
        field = request.args.get("field")
        filters = []

        if q:
            # The field exists as an exposed column
            if Challenges.__mapper__.has_property(field):
                filters.append(getattr(Challenges, field).like("%{}%".format(q)))

        query = Challenges.query.filter(*filters).order_by(Challenges.id.asc())
        challenges_pre = query.all()
        total = query.count()

        challenges = []
        for n in challenges_pre:
            author = getUserForChallenge(n.id)
            date = getCreationDate(n.id)
            lchange = getLastChanged(n.id)
            challenges.append(
                UserChallenge(
                    n.id,
                    n.name,
                    n.category,
                    author,
                    n.value,
                    n.type,
                    n.state,
                    date,
                    lchange=lchange,
                )
            )

        if res[0]:
            return merge_text(
                res[0],
                render_template(
                    "adminChallenges.html",
                    challenges=challenges,
                    total=total,
                    q=q,
                    field=field,
                ),
            )

    run_after_route(app, "admin.challenges_listing", challenges_listing)

    @admins_only
    def delete_user(user_id):
        if request.method == "DELETE":
            UserChallenges.query.filter_by(user=user_id).delete()

    run_before_route(app, "api.users_user_public", delete_user)

    # config page api call
    @app.route("/userchallenge/api/config/<configType>", methods=["GET", "POST"])
    @admins_only
    def toggle_configs(configType):
        key = configType
        newstate = toggle_config(key)
        data = "disabled"
        if newstate:
            data = "enabled"

        return {"success": True, "data": data, "id": key}

    # user view challenge list
    @app.route("/userchallenge/challenges", methods=["GET", "POST"])
    @userChallenge_allowed
    def view_challenges():
        # TODO: add custom html extension of admin/challenges/challenges
        #      change methods to check for rights and only display challenges by user
        #      add custom html to change challenge editing to be available to users
        #
        #      add other plugin to modify challenge creation?

        q = request.args.get("q")
        field = request.args.get("field")
        challenges = getAllUserChallenges(q, field)
        total = len(challenges)

        # return render_template('userChallenges.html',challenges=challenges,total=total,q=q,field=field)
        return render_template(
            "userChallenges.html", challenges=challenges, total=total, q=q, field=field
        )

    # new challenge user
    @app.route("/userchallenge/challenges/new", methods=["GET"])
    @userChallenge_allowed
    def view_newChallenge():
        types = CHALLENGE_CLASSES.keys()
        return render_template("createUserChallenge.html", types=types)

    # edit challenge
    @app.route("/userchallenge/challenges/<int:challenge_id>", methods=["GET"])
    @owned_by_user
    @userChallenge_allowed
    def updateChallenge(challenge_id):
        # TODO: update logic to work with plugin
        challenges = dict(
            Challenges.query.with_entities(Challenges.id, Challenges.name).all()
        )
        challenge = Challenges.query.filter_by(id=challenge_id).first_or_404()
        solves = (
            Solves.query.filter_by(challenge_id=challenge.id)
            .order_by(Solves.date.asc())
            .all()
        )
        flags = Flags.query.filter_by(challenge_id=challenge.id).all()

        try:
            challenge_class = get_chal_class(challenge.type)
        except KeyError:
            abort(
                500,
                f"The underlying challenge type ({challenge.type}) is not installed. This challenge can not be loaded.",
            )

        update_j2 = render_template(
            challenge_class.templates["update"].lstrip("admin/challenges/"),
            challenge=challenge,
        )

        if isReadOnly():
            if type(update_j2) == str:
                update_j2 = update_j2.replace(
                    '	<div>\n\t\t<button class="btn btn-success btn-outlined float-right" type="submit">\n\t\t\tUpdate\n\t\t</button>\n\t</div>',
                    "",
                )

        update_script = url_for(
            "views.static_html",
            route=challenge_class.scripts["update"].lstrip("/admin/challenges/"),
        )

        return render_template(
            "editUserChallenge.html",
            update_template=update_j2,
            update_script=update_script,
            challenge=challenge,
            challenges=challenges,
            solves=solves,
            flags=flags,
        )

    # api rerouting
    ## challenges
    challenges.load(app)
    ## FLAGS
    flags.load(app)
    # FILES
    files.load(app)
    # TOPICS
    topics.load(app)
    # TAGS
    tags.load(app)
    # Hints
    hints.load(app)

    # Requirements
    @app.route(
        "/userchallenge/api/challenges/<challenge_id>/requirements", methods=["GET"]
    )
    def getReqs(challenge_id):
        challenge = Challenges.query.filter_by(id=challenge_id).first_or_404()
        return {"success": True, "data": challenge.requirements}
    
    # Comments
    comments.load(app)
    # attempts
    attempts.load(app)
