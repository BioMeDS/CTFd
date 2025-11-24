
from CTFd.plugins.emailnotifications.forms import settings, users


class _FormsWrapper:
    pass

forms = _FormsWrapper()

forms.settings = settings
forms.users = users