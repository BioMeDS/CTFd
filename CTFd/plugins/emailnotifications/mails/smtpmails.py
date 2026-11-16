import html as html_lib
import re
import smtplib
from email.message import EmailMessage
from email.utils import formataddr, formatdate, make_msgid, parseaddr
from socket import timeout

from CTFd.utils import get_app_config, get_config


def _html_to_text(markup):
    """Rough plain-text fallback for the text/plain part of HTML mails."""
    text = re.sub(r"(?is)<(script|style).*?</\1>", "", markup)
    text = re.sub(r"(?i)<br\s*/?>|</(p|div|h[1-6]|li|tr)>", "\n", text)
    text = re.sub(r"<[^>]+>", "", text)
    text = html_lib.unescape(text)
    return re.sub(r"\n{3,}", "\n\n", text).strip()


def sendmail_smtp(addr, text, subject, html=False):
    """Send a mail to a single recipient via SMTP."""
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
        if html:
            msg.set_content(_html_to_text(text))
            msg.add_alternative(text, subtype="html")
        else:
            msg.set_content(text)

        msg["Subject"] = subject
        msg["From"] = mailfrom_addr
        msg["To"] = addr
        # RFC 5322 requires Date; Message-ID is expected by iCloud/Gmail filters
        msg["Date"] = formatdate(usegmt=True)
        msg["Message-ID"] = make_msgid(domain=parseaddr(mailfrom_addr)[1].rpartition("@")[2] or None)
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