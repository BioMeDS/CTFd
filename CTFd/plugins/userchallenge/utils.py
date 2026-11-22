import datetime
import functools

from flask import abort, redirect, request, url_for

from CTFd.models import Challenges, db
from CTFd.utils import get_config
from CTFd.utils.user import get_current_user, get_user_attrs, is_admin


class UserChallenges(db.Model):
    __tablename__ = "UserChallenges"
    id = db.Column(db.Integer, primary_key=True)
    user = db.Column(db.Integer,db.ForeignKey('users.id', ondelete='CASCADE', onupdate='CASCADE'))
    challenge = db.Column(db.Integer,db.ForeignKey('challenges.id', ondelete='CASCADE', onupdate='CASCADE'))
    date = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    changed = db.Column(db.DateTime, default=datetime.datetime.utcnow)

    def __init__(self,user,challenge,date):
        self.user = user
        self.challenge = challenge
        self.date = date


class UserFiles(db.Model):
    __tablename__ = "UserFiles"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"))
    file_id = db.Column(db.Integer, db.ForeignKey("files.id", ondelete="CASCADE"))
    
    def __init__(self,user,file):
            self.user_id = user
            self.file_id = file
        
def add_User_Link(challenge_id):
    userchallenge = UserChallenges(get_current_user().id,challenge_id,datetime.datetime.utcnow())
    db.session.add(userchallenge)
    db.session.commit()

def userChallenge_allowed(f):
    """
    Decorator that requires the user to be authed and userchallenges to be active
    :param f:
    :return:
    """

    @functools.wraps(f)
    def userChallenge_wrapper(*args, **kwargs):
        value = get_config('allowUserChallenges')

        if (value and get_current_user()) or is_admin():
            return f(*args, **kwargs)
        else:
            if request.content_type == "application/json":
                abort(403)
            else:
                return redirect(url_for("auth.login", next=request.full_path))
    return userChallenge_wrapper

def owned_by_user(f):
    """
    Decorator that requires the accessed challenge to be registered under the user's name
    :param f:
    :return:
    """
    @functools.wraps(f)
    def is_owned_wrapper(*args, **kwargs):
        user = db.session.query(UserChallenges.user).filter(UserChallenges.challenge == kwargs.get("challenge_id")).first()
        db.session.commit()
        if (user and get_current_user() and user[0] == get_current_user().id) or is_admin():
            return f(*args, **kwargs)
        else:
            if request.content_type == "application/json":
                abort(403)
            else:
                return redirect(url_for("auth.login", next=request.full_path))
    return is_owned_wrapper

def getAllUserChallenges(q,field):
    filters =[]
    
    if q:
        # The field exists as an exposed column
        if Challenges.__mapper__.has_property(field):
            filters.append(getattr(Challenges, field).like("%{}%".format(q)))

    filters.append(getattr(UserChallenges,'user').like(get_current_user().id))

    query = db.session.query(UserChallenges.challenge).filter(*filters)
    challenge_ids_raw = query.all()
    challenge_ids = []
    for chal in challenge_ids_raw:
        challenge_ids.append(chal[0])        
    challenges = Challenges.query.filter(Challenges.id.in_(challenge_ids)).all()
    return challenges

def getUserForChallenge(id):
    query = db.session.query(UserChallenges.user).filter(getattr(UserChallenges,'challenge').like(id)).first()
    return 'system-created' if query == None else get_user_attrs(query[0]).name

def getCreationDate(id):
    db.session.execute('alter Table UserChallenges add column if not exists date datetime')
    query = db.session.query(UserChallenges.date).filter(getattr(UserChallenges,'challenge').like(id)).first()
    db.session.commit()
    if(query == None):
        return "no date saved"
    elif (query[0]== None):
        return "no date saved"
    else:
        return query[0]
    
def getLastChanged(id):
    db.session.execute('alter Table UserChallenges add column if not exists changed datetime')
    query = db.session.query(UserChallenges.changed).filter(getattr(UserChallenges,'challenge').like(id)).first()
    db.session.commit()
    if(query == None):
        return getCreationDate(id)
    elif(query[0] == None):
        return getCreationDate(id)
    else:
        return query[0]
   
def setLastChanged(id):
    db.session.execute('alter Table UserChallenges add column if not exists changed datetime')
    time = datetime.datetime.utcnow()
    query = db.session.query(UserChallenges).filter(getattr(UserChallenges,'challenge').like(id)).first()
    if(query != None):
        setattr(query,'changed',time)
    db.session.commit()

def isReadOnly():
    return get_config('isReadOnlyUserChallenges')

def showLink():
    if get_config('allowUserChallenges'):
        if isReadOnly() and not getAllUserChallenges("",""):
            return False
        else:
            return True
    else:
        return False

def ReadOnly(f):
    """
    Decorator that prevents the user from making changes if the read only setting is enabled, but allows admins to bypass this restriction
    :param f:
    :return:
    """
    @functools.wraps(f)
    def is_owned_wrapper(*args, **kwargs):
        if not isReadOnly() or is_admin():
            return f(*args, **kwargs)
        else:
            return{
                    "success": True,
                    "errors": "Read Only Upload Forbidden",
                }, 200
    return is_owned_wrapper

def user_owns_challenge(challenge_id):
    """
    Returns True if the current user created the given challenge (or is an admin)
    """
    if is_admin():
        return True
    user = get_current_user()
    if user is None or challenge_id is None:
        return False
    try:
        challenge_id = int(challenge_id)
    except (TypeError, ValueError):
        return False
    link = UserChallenges.query.filter_by(challenge=challenge_id, user=user.id).first()
    return link is not None


def require_challenge_owner(challenge_id):
    """
    Aborts with 403 unless the current user created the challenge (or is an admin)
    """
    if not user_owns_challenge(challenge_id):
        abort(403)


def challenge_id_from(data):
    """
    Returns the challenge id referenced by a request body, accepting both of the
    keys CTFd uses ("challenge_id" and "challenge")
    """
    if not data:
        return None
    value = data.get("challenge_id")
    if value is None:
        value = data.get("challenge")
    return value


def require_body_challenge_owner(data):
    """
    For updates: if the request body (re)targets a challenge, the user must own it
    """
    if data and ("challenge_id" in data or "challenge" in data):
        require_challenge_owner(challenge_id_from(data))


def user_owns_file(file_id):
    """
    A user owns a file if they uploaded it, or if it is attached to one of their
    challenges or to the solution of one of their challenges
    """
    from CTFd.models import Files, Solutions

    if is_admin():
        return True
    user = get_current_user()
    if user is None:
        return False
    if UserFiles.query.filter_by(user_id=user.id, file_id=file_id).first():
        return True
    f = Files.query.filter_by(id=file_id).first()
    if f is None:
        return False
    if f.type == "challenge":
        return user_owns_challenge(getattr(f, "challenge_id", None))
    if f.type == "solution":
        solution = Solutions.query.filter_by(
            id=getattr(f, "solution_id", None)
        ).first()
        return solution is not None and user_owns_challenge(solution.challenge_id)
    return False


_columns_ensured = False


def _ensure_userchallenge_columns():
    """Adds the date/changed columns on old databases (once per process)"""
    global _columns_ensured
    if _columns_ensured:
        return
    db.session.execute('alter Table UserChallenges add column if not exists date datetime')
    db.session.execute('alter Table UserChallenges add column if not exists changed datetime')
    db.session.commit()
    _columns_ensured = True


def getChallengeInfos(challenge_ids):
    """
    Author, creation date and last change for many challenges in one query.
    Same fallbacks as getUserForChallenge / getCreationDate / getLastChanged.
    """
    from CTFd.models import Users

    _ensure_userchallenge_columns()
    links = (
        db.session.query(
            UserChallenges.challenge, Users.name, UserChallenges.date, UserChallenges.changed
        )
        .outerjoin(Users, Users.id == UserChallenges.user)
        .filter(UserChallenges.challenge.in_(list(challenge_ids)))
        .all()
    )
    found = {}
    for challenge_id, name, date, changed in links:
        found.setdefault(challenge_id, (name, date, changed))

    infos = {}
    for challenge_id in challenge_ids:
        name, date, changed = found.get(challenge_id, (None, None, None))
        creation = date if date is not None else "no date saved"
        infos[challenge_id] = {
            "author": name if challenge_id in found else "system-created",
            "creation": creation,
            "lastChanged": changed if changed is not None else creation,
        }
    return infos
