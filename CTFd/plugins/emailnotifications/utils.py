

import re

from CTFd.models import db
from CTFd.plugins.emailnotifications.mails.mailgunmails import (
    sendmail as sendmail_mailgun,
)
from CTFd.plugins.emailnotifications.mails.smtpmails import sendmail_smtp
from flask import url_for
from CTFd.utils.config import get_mail_provider
from CTFd.utils.email import sendmail
from CTFd.utils.logging import log


IMAGE_SRC_PATTERN = re.compile(
    r'(<img\b[^>]*?\bsrc=["\'])(/files/[^"\']+)(["\'])',
    re.IGNORECASE,
)


def _add_static_image_sources(content):
    def replace_image_source(match):
        image_url = url_for(
            "views.files",
            path=match.group(2).removeprefix("/files/"),
            _external=True,
        )
        return f"{match.group(1)}{image_url}{match.group(3)}"

    return IMAGE_SRC_PATTERN.sub(replace_image_source, content)


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
    # one separate mail per user, each addressed to that user
    users = get_all_users_checked()
    text = _add_static_image_sources(notif["content"])
    title = notif["title"]
    for addr in users:
        _send_notification_email(addr, text, title)


def _send_notification_email(addr, text, title):
    provider = get_mail_provider()

    if provider == "smtp":
        log(
            "registrations",
            "################# sent as smtp",
        )
        result = sendmail_smtp(addr, text, title, html=True)
        log(
            "registrations",
            "################# has done this: {result}",
            result=result,
        )
    elif provider == "mailgun":
        result = sendmail_mailgun(addr, text, title)
    else:
        result = sendmail(addr, text, title)
        
    if result[0]:    
        log(
            "registrations",
            "[{date}] {ip} - email notification sent to {addr}: {title}",
            addr=addr,
            title=title,
        )


def get_user_check(user_id):
    query = db.session.query(UserNotifs).filter(UserNotifs.user == user_id).first()
    return "true" if query and query.data else "false"
