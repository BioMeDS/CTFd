from pathlib import Path

from flask import Blueprint, render_template, request

from CTFd.constants.languages import SELECT_LANGUAGE_LIST
from CTFd.plugins.LuaUtils import ConfigPanel, _LuaAsset, toggle_config
from CTFd.utils import get_config, set_config
from CTFd.utils.decorators import admins_only
from CTFd.utils.logging import log
from CTFd.utils.plugins import override_template

inlineTranslation = Blueprint(
    "inlinetranslation",
    __name__,
    template_folder="templates",
    static_folder="staticAssets",
)


def registerTemplate(old_path, new_path):
    dir_path = Path(__file__).parent.resolve()
    template_path = dir_path / "templates" / new_path
    override_template(old_path, open(template_path).read())


def load(app):
    app.jinja_env.globals.update(InlineTranslationAssets=_LuaAsset("inlinetranslation"))

    set_config("inlineTranslationStandard", get_config("default_locale"))

    app.register_blueprint(inlineTranslation, url_prefix="/inlinetranslation")

    registerTemplate("base.html", "inlinebase.html")
    registerTemplate("admin/base.html", "admininlinebase.html")
    registerTemplate("page.html", "inlinepage.html")
    registerTemplate("admin/page.html", "inlinepage.html")

    @app.route("/admin/inlineTranslation/config/<configType>", methods=["GET"])
    @admins_only
    def toggle_inlines(configType):
        key = configType
        newstate = toggle_config(key)
        data = "disabled"
        if newstate:
            data = "enabled"

        return {"success": True, "data": data, "id": key}

    @app.route("/admin/inlineTranslation/config/<configType>", methods=["POST"])
    @admins_only
    def set_inlines(configType):
        key = configType
        value = request.get_json()["value"]
        set_config(key, value)
        return {"success": True}

    @app.route("/admin/inlineTranslation")
    @admins_only
    def inline_config():
        standard = get_config("inlineTranslationStandard")
        configs = [
            ConfigPanel(
                "Standard Language",
                "Set the standard language.",
                standard,
                "inlineTranslationStandard",
                SELECT_LANGUAGE_LIST,
            )
        ]
        return render_template("inlineConfig.html", configs=configs)

    @app.route("/admin/inlineTranslation/standardlanguage", methods=["GET", "POST"])
    def get_standard_language():
        standard = get_config("inlineTranslationStandard")
        return {"success": True, "data": standard}
