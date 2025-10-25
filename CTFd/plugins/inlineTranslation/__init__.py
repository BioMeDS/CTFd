import os
from pathlib import Path
from CTFd.plugins.LuaUtils import _LuaAsset, ConfigPanel, toggle_config
from CTFd.utils import get_config, set_config
from CTFd.utils.decorators import admins_only
from CTFd.utils.logging import log
from CTFd.utils.plugins import override_template
from CTFd.utils.user import get_current_user
from flask import render_template,Blueprint,current_app


inlineTranslation = Blueprint('inlinetranslation',__name__,template_folder='templates',static_folder ='staticAssets')

def registerTemplate(old_path, new_path):
        dir_path = Path(__file__).parent.resolve()
        template_path = dir_path/'templates'/new_path
        override_template(old_path,open(template_path).read())

def load(app):

    app.jinja_env.globals.update(InlineTranslationAssets=_LuaAsset("inlinetranslation"))

    app.register_blueprint(inlineTranslation,url_prefix='/userchallenge')

    registerTemplate('page.html','inlinepage.html')

    @app.route("/admin/inlineTranslation/config/<configType>",methods=['GET','POST'])
    @admins_only
    def toggle_inlines(configType):
        key = configType
    
        newstate = toggle_config(key)
        data = "disabled"
        if newstate:
            data = "enabled"
        
        return {"success":True,"data":data,"id":key}
    
    @app.route("/admin/InlineTranslation")
    @admins_only
    def inline_config():
        standard = get_config("inlineTranslationStandard")
        if (standard):
             toggle = "enabled"
        else:
             toggle = "disabled"
        configs = [
             ConfigPanel("Standard Language","Set the standard language.",toggle,"inlineTranslationStandard")
        ]
        return render_template('notificationConfig.html',configs = configs)

    @app.route("/admin/inlineTranslation/standardlanguage",methods=['GET','POST'])
    def get_standard_language():
        standard = get_config("inlineTranslationStandard")
        return {"success":True,"data":standard}