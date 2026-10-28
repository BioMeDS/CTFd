import requests
from email.utils import formataddr

from CTFd.utils import get_app_config, get_config


def sendmail(addr, text, subject):
    ctf_name = get_config("ctf_name")
    mailfrom_addr = get_config("mailfrom_addr") or get_app_config("MAILFROM_ADDR")
    mailfrom_addr = formataddr((ctf_name, mailfrom_addr))

    mailgun_base_url = get_config("mailgun_base_url") or get_app_config(
        "MAILGUN_BASE_URL"
    )
    mailgun_api_key = get_config("mailgun_api_key") or get_app_config("MAILGUN_API_KEY")

    try:
        response = requests.post(
            mailgun_base_url + "/messages",
            auth=("api", mailgun_api_key),
            data={
                "from": mailfrom_addr,
                "to": [addr],
                "subject": subject,
                "text": text,
                "html": text,
            },
            timeout=1.0,
        )
    except requests.RequestException as error:
        return False, "{} exception occurred while handling your request".format(
            type(error).__name__
        )

    if response.status_code == 200:
        return True, "Email sent"
    return False, "Mailgun settings are incorrect"
