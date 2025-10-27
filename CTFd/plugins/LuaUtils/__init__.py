import functools
from CTFd.cache import cache
from CTFd.utils import _get_asset_json, get_asset_json, get_config, set_config
from CTFd.utils.helpers import markup
from flask import current_app,url_for
import os

def load(app):
    cache.delete_memoized(_get_asset_json)
    return

class _LuaAsset():
    def __init__(self,directory):
        self.directory = directory
    def manifest(self, _return_none_on_load_failure=False):
        file_path = os.path.join(
            current_app.root_path, "plugins",self.directory,"staticAssets","manifest.json"
        )

        try:
            manifest = get_asset_json(path=file_path)
        except FileNotFoundError as e:
            # This check allows us to determine if we are on a legacy theme and fallback if necessary
            if _return_none_on_load_failure:
                manifest = None
            else:
                raise e
        return manifest

    def js(self, asset_key, type="module", defer=False, extra=""):
        asset = self.manifest()[asset_key]
        entry = asset["file"]
        imports = asset.get("imports", [])

        # Add in extra attributes. Note that type="module" imples defer
        _attrs = ""
        if type:
            _attrs = f'type="{type}" '
        if defer:
            _attrs += "defer "
        if extra:
            _attrs += extra

        html = ""
        for i in imports:
            # TODO: Needs a better recursive solution
            i = self.manifest()[i]["file"]
            url = url_for(self.directory+".static", filename=i)
            html += f'<script {_attrs} src="{url}"></script>'
        url = url_for(self.directory+".static", filename=entry)
        html += f'<script {_attrs} src="{url}"></script>'
        return markup(html)

class ConfigPanel():
    """Data structure for config panel html"""
    def __init__(self, name,desc,toggle,config,*options):
        self.name = name
        self.desc = desc
        self.toggle = toggle
        self.config = config
        self.options = options[0] if options else None

def toggle_config(key):
    """toggles provided config"""
    value = get_config(key)
    if value:
        set_config(key,'false')
        return False
    else:
        set_config(key,'true')
        return True

def run_as_decorator(function,*last):
    """returns decorator running function before decorated function"""
    def decorator(f):
        """
        decorator that runs function before decorated function
        :param f:
        :return:
        """
        @functools.wraps(f)
        def is_owned_wrapper(*args, **kwargs):
            if last:
                ret = f(*args,**kwargs)
                function(ret + list(*args), **kwargs)
                return ret
            else:
                function(*args, **kwargs)
                return f(*args, **kwargs)
        return is_owned_wrapper
    return decorator

def run_before_route(app,key,function):
    """ runs provided function before given app.view_functions function (key)"""
    delete_user_decorator = run_as_decorator(function)
    app.view_functions[key] = delete_user_decorator(app.view_functions[key])

def run_after_route(app,key,function):
    """ runs provided function after given app.view_functions function (key) with response as first input"""
    delete_user_decorator = run_as_decorator(function,True)
    app.view_functions[key] = delete_user_decorator(app.view_functions[key])