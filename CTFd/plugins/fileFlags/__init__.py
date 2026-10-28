import re

from flask import request

from CTFd.models import Files, Flags
from CTFd.plugins.LuaUtils import run_after_route, run_before_route

from .textFileFlag import load as text_load

FILE_INPUT = """
<div class="form-group mt-3 file-flag-upload">
  <label for="file-flag-upload">Submit text file</label>
  <input
    id="file-flag-upload"
    class="form-control"
    type="file"
    accept="text/*,.txt,.csv,.log,.json,.xml,.md,.yaml,.yml"
    @change="uploadTextFile($event)"
  >
  <small class="form-text text-muted" x-show="fileUploadMessage" x-text="fileUploadMessage"></small>
</div>
"""

FILE_UPLOAD_BEHAVIOR = """
<div
  x-init="
    fileUploadMessage = '';
    uploadTextFile = async (event) => {
      const file = event.target.files[0];
      if (!file) return;
      fileUploadMessage = 'Uploading...';
      const data = new FormData();
      data.append('file', file);
      data.append('nonce', CTFd.config.csrfNonce);
      data.append('type', 'standard');
      try {
        const response = await fetch(CTFd.config.urlRoot + '/userchallenge/api/files', {
          method: 'POST',
          body: data
        });
        const result = await response.json();
        if (!response.ok || !result.success || !result.data || result.data.length !== 1) {
          throw new Error('The upload did not return a file.');
        }
        const fileUrl = CTFd.config.urlRoot + '/files/' + result.data[0].location;
        submission = fileUrl;
        const submissionInput = document.getElementById('challenge-input');
        if (submissionInput) {
          submissionInput.value = fileUrl;
          submissionInput.dispatchEvent(new Event('input', { bubbles: true }));
        }
        fileUploadMessage = 'File uploaded.';
      } catch (error) {
        fileUploadMessage = 'Upload failed.';
        event.target.value = '';
      }
    }
  "
></div>
"""

PREVIEW_UPLOAD_SCRIPT = """
<script>
(function () {
  function addTextFileUpload() {
    const submissionInput = document.getElementById("challenge-input");
    if (!submissionInput || document.getElementById("file-flag-upload")) {
      return;
    }

    submissionInput.type = "hidden";
    const upload = document.createElement("input");
    upload.id = "file-flag-upload";
    upload.className = "form-control";
    upload.type = "file";
    upload.accept = "text/*,.txt,.csv,.log,.json,.xml,.md,.yaml,.yml";
    submissionInput.parentElement.insertBefore(upload, submissionInput);

    upload.addEventListener("change", async function () {
      const file = upload.files[0];
      if (!file) return;

      const data = new FormData();
      data.append("file", file);
      data.append("nonce", CTFd.config.csrfNonce);
      data.append("type", "standard");

      const response = await fetch(
        CTFd.config.urlRoot + "/userchallenge/api/files",
        { method: "POST", body: data }
      );
      const result = await response.json();
      if (!response.ok || !result.success || !result.data || result.data.length !== 1) {
        upload.value = "";
        return;
      }

      const fileUrl = CTFd.config.urlRoot + "/files/" + result.data[0].location;
      submissionInput.value = fileUrl;
      submissionInput.dispatchEvent(new Event("input", { bubbles: true }));
      submissionInput.dispatchEvent(new Event("change", { bubbles: true }));
    });
  }

  const observer = new MutationObserver(addTextFileUpload);
  observer.observe(document.documentElement, { childList: true, subtree: true });
  addTextFileUpload();
})();
</script>
"""


def _is_text_file_challenge(challenge_id):
    return Flags.query.filter_by(
        challenge_id=challenge_id, type="textFile"
    ).first() is not None


def _add_file_upload_to_challenge(response, *args, **kwargs):
    result = response[0]
    if isinstance(result, tuple):
        result = result[0]

    if hasattr(result, "get_json"):
        data = result.get_json()
    else:
        data = result

    challenge = data.get("data", {})
    challenge_id = challenge.get("id")
    if not challenge_id or not _is_text_file_challenge(challenge_id):
        return

    view = _inject_file_upload(challenge.get("view", ""))
    if view == challenge.get("view", ""):
        return

    challenge["view"] = view
    return {"success": True, "data": challenge}


def _inject_file_upload(view):
    input_pattern = re.compile(
        r"<input\b(?=[^>]*\bid=[\"']challenge-input[\"'])[^>]*>",
        re.IGNORECASE,
    )
    if "file-flag-upload" in view:
        return view

    def hide_submission_input(match):
        input_tag = match.group(0)
        input_tag = re.sub(
            r'\btype\s*=\s*([\'"])text\1',
            r'type="hidden"',
            input_tag,
            count=1,
            flags=re.IGNORECASE,
        )
        return FILE_INPUT + FILE_UPLOAD_BEHAVIOR + input_tag

    view, replacements = input_pattern.subn(
        hide_submission_input,
        view,
        count=1,
    )
    if replacements == 0:
        return view
    return view


def _add_file_upload_to_preview(response, challenge_id, *args, **kwargs):
    if not _is_text_file_challenge(challenge_id):
        return

    content = response[0]
    if not hasattr(content, "get_data"):
        return

    view = content.get_data(as_text=True)
    if "file-flag-upload" in view:
        return

    if "</body>" in view:
        view = view.replace("</body>", PREVIEW_UPLOAD_SCRIPT + "</body>", 1)
    else:
        view += PREVIEW_UPLOAD_SCRIPT
    content.set_data(view)
    return content


def _validate_file_submission():
    if not request.is_json:
        request_data = request.form
    else:
        request_data = request.get_json(silent=True) or {}

    challenge_id = request_data.get("challenge_id")
    submission = request_data.get("submission", "")
    if not challenge_id or not _is_text_file_challenge(challenge_id):
        return

    if not re.fullmatch(r"/files/.+", submission):
        return

    location = submission.removeprefix("/files/")
    if Files.query.filter_by(location=location).first() is None:
        return {
            "success": True,
            "data": {
                "status": "incorrect",
                "message": "The uploaded file could not be found.",
            },
        }


def load(app):
    text_load(app)
    run_after_route(app, "api.challenges_challenge", _add_file_upload_to_challenge)
    for endpoint in ("admin.challenges_preview", "render_preview"):
        if endpoint in app.view_functions:
            run_after_route(app, endpoint, _add_file_upload_to_preview)
        else:
            @app.after_request
            def add_file_upload_to_late_preview(response):
                if request.endpoint != endpoint:
                    return response

                challenge_id = request.view_args.get("challenge_id")
                if challenge_id and _is_text_file_challenge(challenge_id):
                    view = _inject_file_upload(response.get_data(as_text=True))
                    response.set_data(view)
                return response
    run_before_route(app, "api.challenges_challenge_attempt", _validate_file_submission)