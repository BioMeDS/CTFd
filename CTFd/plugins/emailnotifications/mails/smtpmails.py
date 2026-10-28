import smtplib
from email.message import EmailMessage
from email.utils import formataddr
from socket import timeout

from CTFd.utils import get_app_config, get_config


def sendmail_hidden(addr, text, subject, html=False):
    ctf_name = get_config("ctf_name")
    mailfrom_addr = get_config("mailfrom_addr") or get_app_config("MAILFROM_ADDR")
    mailfrom_addr = formataddr((ctf_name, mailfrom_addr))

    data = {
        "host": get_config("mail_server") or get_app_config("MAIL_SERVER"),
        "port": int(get_config("mail_port") or get_app_config("MAIL_PORT")),
    }
    username = get_config("mail_username") or get_app_config("MAIL_USERNAME")
    password = get_config("mail_password") or get_app_config("MAIL_PASSWORD")
    tls = get_config("mail_tls") or get_app_config("MAIL_TLS")
    ssl = get_config("mail_ssl") or get_app_config("MAIL_SSL")
    auth = get_config("mail_useauth") or get_app_config("MAIL_USEAUTH")

    if username:
        data["username"] = username
    if password:
        data["password"] = password
    if tls:
        data["TLS"] = tls
    if ssl:
        data["SSL"] = ssl
    if auth:
        data["auth"] = auth

    smtp = None
    try:
        smtp = get_smtp(**data)

        msg = EmailMessage()
        msg.set_content(text)
        if html:
            msg.add_alternative(text, subtype="html")

        msg["Subject"] = subject
        msg["From"] = mailfrom_addr
        msg["To"] = mailfrom_addr
        msg["Bcc"] = addr
        custom_smtp = bool(get_config("mail_server"))

        if custom_smtp:
            smtp.send_message(msg)
        else:
            mailsender_addr = get_app_config("MAILSENDER_ADDR")
            smtp.send_message(msg, from_addr=mailsender_addr)

        smtp.close()
        return True, "Email sent"
    except smtplib.SMTPException as error:
        if smtp is not None:
            smtp.close()
        return False, str(error)
    except timeout:
        if smtp is not None:
            smtp.close()
        return False, "SMTP server connection timed out"
    except Exception as error:
        if smtp is not None:
            smtp.close()
        return False, str(error)


def get_smtp(host, port, username=None, password=None, TLS=None, SSL=None, auth=None):
    if SSL:
        smtp = smtplib.SMTP_SSL(host, port, timeout=3)
    else:
        smtp = smtplib.SMTP(host, port, timeout=3)

    if TLS:
        smtp.starttls()

    if auth:
        smtp.login(username, password)
    return smtp