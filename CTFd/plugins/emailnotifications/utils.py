

from CTFd.models import db
from CTFd.utils import get_config
from CTFd.utils.email import sendmail


class UserNotifs(db.Model):
    __tablename__ = "UserNotifs"
    id = db.Column(db.Integer, primary_key=True)
    user = db.Column(
        db.Integer, db.ForeignKey("users.id", ondelete="CASCADE", onupdate="CASCADE")
    )
    email = db.Column(
        db.String(128),
        db.ForeignKey("users.email", ondelete="CASCADE", onupdate="CASCADE"),
        unique=True,
    )
    data = db.Column(db.Boolean, default=False)

    def __init__(self, user, data):
        self.user = user.id
        self.email = user.email
        self.data = data


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
    if get_config("emailPrivacyNotif"):
        # send mail through inbuilt api for each user
        for addr in users:
            text = notif["content"]
            title = notif["title"]
            sendmail(addr, text, title)
    else:
        # send mail through inbuilt api to every user in addr. makes all adresses public
        if len(users) > 1:
            addr = ", ".join(users)
        elif len(users) > 0:
            addr = users[0]
        else:
            return

        text = notif["content"]
        title = notif["title"]

        sendmail(addr, text, title)
    return


def get_user_check(user_id):
    query = db.session.query(UserNotifs).filter(UserNotifs.user == user_id).first()
    return "true" if query and query.data else "false"
