import re
from urllib.parse import urlparse

from flask import request
from CTFd.models import Files, Flags, db
from CTFd.plugins import register_plugin_assets_directory
from CTFd.plugins.flags import FLAG_CLASSES, BaseFlag, FlagException
from CTFd.plugins.LuaUtils import run_before_route
from CTFd.utils.logging import log
from CTFd.utils.uploads import get_uploader


class CTFdTFileFlag(BaseFlag):
    name = "textFile"
    templates = {
        "create": "/plugins/fileFlags/textFileFlag/assets/create.html",
        "update": "/plugins/fileFlags/textFileFlag/assets/edit.html",
    }

    @staticmethod
    def compare(chal_key_obj, provided):
        def get_file_location(file_url):
            if isinstance(file_url, bytes):
                file_url = file_url.decode("utf-8")

            path = urlparse(file_url).path
            prefix = "/files/"
            log(
                "registrations",
                "[{date}] {ip} - text file flag URL: {file_url}; parsed path: {path}",
                file_url=file_url,
                path=path,
            )
            if not path.startswith(prefix):
                raise FlagException("Flag must be a CTFd file URL")

            location = path[len(prefix) :]
            file_record = Files.query.filter_by(location=location).first()
            if file_record is None:
                raise FlagException("The file URL does not reference an uploaded file")
            return file_record.location

        log(
            "registrations",
            "[{date}] {ip} - comparing text file flag values; stored: {stored}, provided: {provided}",
            stored=chal_key_obj.content,
            provided=provided,
        )
        try:
            saved_location = get_file_location(chal_key_obj.content)
            provided_location = get_file_location(provided)
            uploader = get_uploader()
            with uploader.open(saved_location, mode="rb") as saved_file:
                saved_content = saved_file.read().decode("utf-8")
            with uploader.open(provided_location, mode="rb") as provided_file:
                provided_content = provided_file.read().decode("utf-8")
        except UnicodeDecodeError:
            raise FlagException("Both files must be valid UTF-8 text files")
        except OSError:
            raise FlagException("Unable to read one of the uploaded files")

        return saved_content == provided_content


def load(app):
    FLAG_CLASSES['textFile'] = CTFdTFileFlag
    register_plugin_assets_directory(app, base_path="/plugins/fileFlags/textFileFlag/assets/")
    
    def delete_text_file_flag(flag_id):
        flag = Flags.query.filter_by(id=flag_id, type="textFile").first()
        if flag is None or not flag.content:
            return

        content = (
            flag.content.decode("utf-8")
            if isinstance(flag.content, bytes)
            else flag.content
        )
        path = urlparse(content).path
        prefix = "/files/"
        if not path.startswith(prefix):
            return

        location = path[len(prefix) :]
        file_record = Files.query.filter_by(location=location).first()
        if file_record is None:
            return

        shared = Flags.query.filter(
            Flags.id != flag.id,
            Flags.content.in_((location, prefix + location, content)),
        ).first()
        if shared is not None:
            return

        get_uploader().delete(file_record.location)
        db.session.delete(file_record)
        db.session.commit()

    if "flagIDdelete" in app.view_functions:
        run_before_route(
            app,
            "flagIDdelete",
            lambda *args, **kwargs: delete_text_file_flag(kwargs.get("flag_id")),
        )
    else:
        @app.before_request
        def delete_text_file_flag_before_request():
            if request.endpoint != "flagIDdelete":
                return

            match = re.fullmatch(r"/userchallenge/api/flags/(\d+)", request.path)
            if match:
                delete_text_file_flag(int(match.group(1)))
    