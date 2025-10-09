from pathlib import Path
from CTFd.plugins.LuaUtils import _LuaAsset, toggle_config
from CTFd.utils.decorators import admins_only
from CTFd.utils.plugins import override_template
from flask import render_template,Blueprint



inlineTranslation = Blueprint('inlineTranslation',__name__,template_folder='templates',static_folder ='staticAssets')

def registerTemplate(old_path, new_path):
        dir_path = Path(__file__).parent.resolve()
        template_path = dir_path/'templates'/new_path
        override_template(old_path,open(template_path).read())

def load(app):
    app.jinja_env.globals.update(InlineTranslationAssets=_LuaAsset("inlineTranslation"))

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
        configs = []
        return render_template('notificationConfig.html',configs = configs)

    registerTemplate('core/page.html','inlinepage.html')
