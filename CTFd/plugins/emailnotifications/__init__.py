from CTFd.utils.modes import TEAMS_MODE
from sqlalchemy.exc import IntegrityError
from sqlalchemy.sql import not_
from CTFd.utils.config import is_teams_mode
from CTFd.utils.decorators.visibility import check_registration_visibility
from CTFd.utils.helpers import get_errors, get_infos, markup
from CTFd.utils import set_config,get_config
from CTFd.utils.decorators import admins_only, authed_only, ratelimit
from CTFd.utils.user import get_current_team, get_current_user
from flask import render_template,request,Blueprint,url_for

from CTFd.utils.email import sendmail

from CTFd.cache import cache
from CTFd.models import Challenges, Tracking, UserTokens, Users, db
from CTFd.plugins.LuaUtils import _LuaAsset, ConfigPanel, merge_text, run_after_route, run_before_route, toggle_config
from CTFd.plugins.emailnotifications.forms import forms


class UserNotifs(db.Model):
    __tablename__ = "UserNotifs"
    id = db.Column(db.Integer, primary_key=True)
    user = db.Column(db.Integer,db.ForeignKey('users.id', ondelete='CASCADE', onupdate='CASCADE'))
    email = db.Column(db.String(128),db.ForeignKey('users.email', ondelete='CASCADE', onupdate='CASCADE'),unique=True)
    data = db.Column(db.Boolean,default=False)

    def __init__(self,user,data):
        self.user = user.id
        self.email = user.email
        self.data = data

cache.memoize()
def _get_all_users_checked():
    # get all users who have checked email notifications
    users = db.session.execute(
        UserNotifs.__table__.select().where(UserNotifs.data == 1)
    ).all()

    return users
    
def get_all_users_checked():
    # do like get config
    users = _get_all_users_checked()
    usermails = []
    for u in users:
        usermails.append(u[2])
    return usermails

def send_mail_all_users(notif):
    users = get_all_users_checked()
    if get_config('emailPrivacyNotif'):
        # send mail through inbuilt api for each user
        for addr in users:
            text = notif["content"]
            title = notif["title"]
            sendmail(addr,text,title)
    else:
        # send mail through inbuilt api to every user in addr. makes all adresses public
        if len(users) > 1 :
            addr = ", ".join(users)
        elif len(users) > 0:
            addr = users[0]
        else: 
            return 

        text = notif["content"]
        title = notif["title"]
        
        sendmail(addr,text,title)
    return

def get_user_check(user_id):
        query = db.session.query(UserNotifs).filter(UserNotifs.user == user_id).first()
        return 'true' if query.data else 'false'

emailNotifs = Blueprint('emailnotifications',__name__,template_folder='templates',static_folder ='staticAssets')

def load(app):

    app.db.create_all()
    #intitalize jinja globals
    app.jinja_env.globals.update(EmailNotifAssets=_LuaAsset("emailnotifications"))
    app.jinja_env.globals.update(NotificationForms=forms)
    app.jinja_env.globals.update(NotificationsGetCheck = get_user_check)
    app.register_blueprint(emailNotifs,url_prefix='/emailnotifications')

    keys = ['sendEmailNotif','allowUserCheckmarkNotif','emailPrivacyNotif']
    for k in keys:
        if get_config(k) == None:
            toggle_config(k)

    # put every existing user in table
    users = db.session.query(Users).all()
    checks = []
    for u in users:
        checks.append(UserNotifs(u,True))
    for c in checks:
        try:
            db.session.add(c)
            db.session.commit()
        except IntegrityError as e:
            db.session.rollback()
            checks = []
    
    @app.route("/admin/emailNotifs/config/<configType>",methods=['GET','POST'])
    @admins_only
    def toggle_notifs(configType):
        key = configType
    
        newstate = toggle_config(key)
        data = "disabled"
        if newstate:
            data = "enabled"
        
        return {"success":True,"data":data,"id":key}
    
    @app.route("/admin/NotificationForwarding")
    @admins_only
    def notif_config():
        notif = get_config('sendEmailNotif')
        check = get_config('allowUserCheckmarkNotif')
        privacy = get_config('emailPrivacyNotif')

        if notif:
            notif = "enabled"
        else :
            notif = "disabled"
        
        if check:
            check = "enabled"
        else :
            check = "disabled"

        if privacy:
            privacy = "enabled"
        else :
            privacy = "disabled"
        
        configs = []
        configs.append(ConfigPanel("Email Notifications",
                                   "Enabeling Email-Notifications sends all Notifications to all users per email.\n Disabling also removes the checkmark option from User profiles.",
                                   notif,'sendEmailNotif'))
        configs.append(ConfigPanel("Opt out",
                                   "Toggles wether Users can opt out of email Notifications or not.",
                                   check,'allowUserCheckmarkNotif'))
        configs.append(ConfigPanel("Privacy",
                                   "Toggles wether Users can see other receivers in mails.",
                                   privacy,'emailPrivacyNotif'))
        
        return render_template('notificationConfig.html',configs = configs)

    @admins_only
    def notification_post(response):
        if response[0].get_json():
            email = get_config("sendEmailNotif")
            if email:
                send_mail_all_users(response[0].get_json()["data"])
            elif email == None:
                set_config("sendEmailNotif",'false')
    run_after_route(app,'api.notifications_notificantion_list',notification_post)

    # put every new user in table
    @check_registration_visibility
    @ratelimit(method="POST", limit=10, interval=5)
    def notif_register():
        # add user checkmark for email notifications
        if(get_current_user()):
            check = UserNotifs(get_current_user(),False)
            db.session.add(check)
            db.session.commit()
            db.session.flush()
    run_after_route(app,'auth.register',notif_register)

    @authed_only
    def notif_settings(toModify):
        infos = get_infos()
        errors = get_errors()

        user = get_current_user()

        if is_teams_mode() and get_current_team() is None:
            team_url = url_for("teams.private")
            infos.append(
                markup(
                    f'In order to participate you must either <a href="{team_url}">join or create a team</a>.'
                )
            )

        tokens = UserTokens.query.filter_by(user_id=user.id).all()

        prevent_name_change = get_config("prevent_name_change")

        if get_config("verify_emails") and not user.verified:
            confirm_url = markup(url_for("auth.confirm"))
            infos.append(
                markup(
                    "Your email address isn't confirmed!<br>"
                    "Please check your email to confirm your email address.<br><br>"
                    f'To have the confirmation email resent please <a href="{confirm_url}">click here</a>.'
                )
            )

        if get_config("allowUserCheckmarkNotif") and get_config('sendEmailNotif'):
            notif_enabled = True
            query = db.session.execute(UserNotifs.__table__.select().where(UserNotifs.user == user.id)).first()
            if query:
                if query[3]:    
                    notifs_mail = 'true'
                else:
                    notifs_mail = 'false'
            else:
                db.session.query(UserNotifs).filter(UserNotifs.user == user.id).update({'data':False})
                db.session.commit()
                notifs_mail ='false'
        else:
            notif_enabled = False
            notifs_mail = 'false'

        template = render_template(
            "notificationSettings.html",
            name=user.name,
            email=user.email,
            language=user.language,
            website=user.website,
            affiliation=user.affiliation,
            country=user.country,
            tokens=tokens,
            prevent_name_change=prevent_name_change,
            infos=infos,
            errors=errors,
            checked=notifs_mail,
            notifications_enabled = notif_enabled
        )

        merged = merge_text(toModify[0],template)

        return merged
    run_after_route(app,'views.settings',notif_settings)

    @authed_only
    def set_notif_check():
        if request.method == "PATCH":
            user = get_current_user()
            data = request.get_json()
            # email notifications update
            checked = True if data["notifications"] == 'true' else False
            db.session.query(UserNotifs).filter(UserNotifs.user == user.id).update({'data':checked})
            db.session.commit()
    run_before_route(app,'api.users_user_private',set_notif_check)
    
    @admins_only
    def patch_user(user_id):
        if get_config('sendEmailNotif') and request.method == "PATCH":
            data = request.get_json()
            checked = True if data["notifications"] == 'true' else False
            UserNotifs.query.filter_by(user=user_id).update({'data':checked})
            db.session.commit()
    run_before_route(app,'api.users_user_public',patch_user)
    
    @admins_only
    def delete_user(user_id):
        if request.method == "DELETE":
            UserNotifs.query.filter_by(user=user_id).delete()
    run_before_route(app,'api.users_user_public',delete_user)

    @admins_only
    def modify_user(res,user_id):
        # Get user object
        user = Users.query.filter_by(id=user_id).first_or_404()

        # Get the user's solves
        solves = user.get_solves(admin=True)

        # Get challenges that the user is missing
        if get_config("user_mode") == TEAMS_MODE:
            if user.team:
                all_solves = user.team.get_solves(admin=True)
            else:
                all_solves = user.get_solves(admin=True)
        else:
            all_solves = user.get_solves(admin=True)

        solve_ids = [s.challenge_id for s in all_solves]
        missing = Challenges.query.filter(not_(Challenges.id.in_(solve_ids))).all()

        # Get IP addresses that the User has used
        addrs = (
            Tracking.query.filter_by(user_id=user_id).order_by(Tracking.date.desc()).all()
        )

        # Get Fails
        fails = user.get_fails(admin=True)

        # Get Awards
        awards = user.get_awards(admin=True)

        # Check if the user has an account (team or user)
        # so that we don't throw an error if they dont
        if user.account:
            score = user.account.get_score(admin=True)
            place = user.account.get_place(admin=True)
        else:
            score = None
            place = None

        return merge_text(res[0],render_template(
            'AdminUser.html',
            solves=solves,
            user=user,
            addrs=addrs,
            score=score,
            missing=missing,
            place=place,
            fails=fails,
            awards=awards,
        ))
    run_after_route(app,'admin.users_detail',modify_user)

    @admins_only
    def modify_users(res):
        q = request.args.get("q")
        field = request.args.get("field")
        page = abs(request.args.get("page", 1, type=int))
        filters = []
        users = []

        if q:
            # The field exists as an exposed column
            if Users.__mapper__.has_property(field):
                filters.append(getattr(Users, field).like("%{}%".format(q)))

        if q and field == "ip":
            users = (
                Users.query.join(Tracking, Users.id == Tracking.user_id)
                .filter(Tracking.ip.like("%{}%".format(q)))
                .order_by(Users.id.asc())
                .paginate(page=page, per_page=50, error_out=False)
            )
        else:
            users = (
                Users.query.filter(*filters)
                .order_by(Users.id.asc())
                .paginate(page=page, per_page=50, error_out=False)
            )

        args = dict(request.args)
        args.pop("page", 1)

        return merge_text(res[0],render_template(
            "AdminUsers.html",
            users=users,
            prev_page=url_for(request.endpoint, page=users.prev_num, **args),
            next_page=url_for(request.endpoint, page=users.next_num, **args),
            q=q,
            field=field,
        ))
    run_after_route(app,'admin.users_listing',modify_users)