import difflib
import functools
import json
import os
import re

from flask import current_app, request, url_for
from flask_babel import get_locale
from flask_babel import gettext as babel_gettext
from flask_babel import ngettext as babel_ngettext

from CTFd.cache import cache
from CTFd.utils import _get_asset_json, get_asset_json, get_config, set_config
from CTFd.utils.decorators import admins_only
from CTFd.utils.helpers import markup


def load(app):
    cache.delete_memoized(_get_asset_json)
    
    # Auto-register translations from all plugins
    plugins_dir = os.path.join(current_app.root_path, "plugins")
    for plugin_name in os.listdir(plugins_dir):
        plugin_dir = os.path.join(plugins_dir, plugin_name)
        if os.path.isdir(plugin_dir):
            translations_file = os.path.join(plugin_dir, 'translations.json')
            if os.path.exists(translations_file):
                register_translations(app, plugin_name, plugin_dir)

    @app.route("/admin/LuaUtils/config/<configType>", methods=["GET"])
    @admins_only
    def toggle_config_type(configType):
        key = configType
        newstate = toggle_config(key)
        data = "disabled"
        if newstate:
            data = "enabled"

        return {"success": True, "data": data, "id": key}

    @app.route("/admin/LuaUtils/config/<configType>", methods=["POST"])
    @admins_only
    def set_config_type(configType):
        key = configType
        value = request.get_json()["value"]
        set_config(key, value)
        return {"success": True}

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
    def __init__(self, name,desc,value,config,*options,isText=False,standard=None):
        self.name = name
        self.desc = desc
        self.toggle = value
        self.config = config
        self.options = options[0] if options else None
        self.isText = isText
        self.standard = standard if standard else value

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
                new = function([ret] + list(*args), **kwargs)
                return new if new else ret
            else:
                new = function(*args, **kwargs)
                ret = f(*args, **kwargs)
                return new if new else ret
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

# https://stackoverflow.com/a/61107079
def merge_text(text1:str, text2:str) -> str:
    """
    Merge two strings by comparing lines and merging text 2 into 1.
    """
    return "\n".join(
        line[2:] for line in difflib.Differ().compare(
            text1.split("\n"),
            text2.split("\n"))
        if not line.startswith("?"))


def insert_in_element(text:str, code:str, element_class:str) -> str:
    """
    Insert code into the middle of every <p> tag within a span with provided class.
    """
    # define regex to find span with provided class and separates into prefix, inner content, and suffix
    container_pattern = r'(<span[^>]*class="' + re.escape(element_class) + r'"[^>]*>)(.*?)(</span>)'
    container_match = re.search(container_pattern, text, re.DOTALL | re.IGNORECASE)
    
    if not container_match:
        return text

    prefix, inner_content, suffix = container_match.groups()

    def modify_p(p_match):
        p_opener, p_inner, p_closer = p_match.groups()
        midpoint = len(p_inner) // 2
        
        # if find opened < without > before midpoint, move midpoint to after next >
        if p_inner.rfind('<', 0, midpoint) > p_inner.rfind('>', 0, midpoint):
            tag_end = p_inner.find('>', midpoint)
            if tag_end != -1:
                midpoint = tag_end + 1
        
        return f"{p_opener}{p_inner[:midpoint]}{code}{p_inner[midpoint:]}{p_closer}"

    p_pattern = r'(<p[^>]*>)(.*?)(</p>)'
    new_inner_content = re.sub(p_pattern, modify_p, inner_content, flags=re.DOTALL | re.IGNORECASE)

    return text[:container_match.start()] + prefix + new_inner_content + suffix + text[container_match.end():]


def load_plugin_translations(plugin_dir):
    """Load translations from a plugin's translations.json"""
    translations_path = os.path.join(plugin_dir, 'translations.json')
    try:
        with open(translations_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        return {}

def register_translations(app, plugin_name, plugin_dir):
    """General-purpose method to integrate plugin translations into Jinja.
    
    Args:
        app: Flask application
        plugin_name: Plugin name (e.g., 'LuaUtils', 'CustomPlugin')
        plugin_dir: Absolute path to plugin directory
    
    Usage:
        from CTFd.plugins.LuaUtils import register_translations
        register_translations(app, 'MyPlugin', os.path.dirname(__file__))
    """
    
    translations = load_plugin_translations(plugin_dir)
    if not translations:
        return
    
    # Store translations in config for database persistence
    for lang, terms in translations.items():
        for term, translation in terms.items():
            key = f"{plugin_name.lower()}_translation_{lang}_{term}"
            set_config(key, translation)
    
    # Wrap Flask-Babel's gettext functions to check plugin translations first
    if not hasattr(app, '_luautils_gettext_wrapped'):
        def wrapped_gettext(s):
            """Check plugin translations first, then fall back to Flask-Babel."""
            for check_plugin in getattr(app, '_registered_plugins', []):
                try:
                    lang = str(get_locale())
                    config_key = f"{check_plugin.lower()}_translation_{lang}_{s}"
                    translation = get_config(config_key)
                    if translation:
                        return translation
                except Exception:
                    pass
            # Fall back to Flask-Babel's default
            return babel_gettext(s)
        
        def wrapped_ngettext(s, p, n):
            """Check plugin translations for plurals, then fall back to Flask-Babel."""
            msg = s if n == 1 else p
            for check_plugin in getattr(app, '_registered_plugins', []):
                try:
                    lang = str(get_locale())
                    config_key = f"{check_plugin.lower()}_translation_{lang}_{msg}"
                    translation = get_config(config_key)
                    if translation:
                        return translation
                except Exception:
                    pass
            # Fall back to Flask-Babel's default
            return babel_ngettext(s, p, n)
        
        # Install our wrapped callables
        app.jinja_env.install_gettext_callables(wrapped_gettext, wrapped_ngettext, newstyle=True)
        app._luautils_gettext_wrapped = True
    
    # Track registered plugins
    if not hasattr(app, '_registered_plugins'):
        app._registered_plugins = []
    if plugin_name not in app._registered_plugins:
        app._registered_plugins.append(plugin_name)
