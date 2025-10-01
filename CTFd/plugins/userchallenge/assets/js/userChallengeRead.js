import "./main";
import $ from "jquery";
import "./compat/json";
import "bootstrap/js/dist/tab";
import CTFd from "./compat/CTFd";;
import { ezQuery, ezAlert, ezToast } from "./compat/ezq";
import { default as helpers } from "./compat/helpers";
import { bindMarkdownEditors } from "./styles";
import Vue from "vue";
import CommentBox from "./components/comments/CommentBox.vue";


function loadChalTemplate(challenge) {
  CTFd._internal.challenge = {};
  $.getScript(CTFd.config.urlRoot + challenge.scripts.view, function () {
    let template_data = challenge.create;
    $("#create-chal-entry-div").html(template_data);
    bindMarkdownEditors();

    $.getScript(CTFd.config.urlRoot + challenge.scripts.create, function () {
      $("#create-chal-entry-div form").submit(function (event) {
        event.preventDefault();
        const params = $("#create-chal-entry-div form").serializeJSON();
        CTFd.fetch("/userchallenge/api/challenges/", {
          method: "POST",
          credentials: "same-origin",
          headers: {
            Accept: "application/json",
            "Content-Type": "application/json",
          },
          body: JSON.stringify(params),
        })
          .then(function (response) {
            return response.json();
          })
          .then(function (response) {
            if (response.success) {
              $("#challenge-create-options #challenge_id").val(
                response.data.id,
              );
              $("#challenge-create-options").modal();
            } else {
              let body = "";
              for (const k in response.errors) {
                body += response.errors[k].join("\n");
                body += "\n";
              }

              ezAlert({
                title: "Error",
                body: body,
                button: "OK",
              });
            }
          });
      });
    });
  });
}

$(() => {
  $(".preview-challenge").click(function (_e) {
    let url = `/userchallenge/challenges/preview/${window.CHALLENGE_ID}`;
    $("#challenge-window").html(
      `<iframe src="${url}" height="100%" width="100%" frameBorder=0></iframe>`,
    );
    $("#challenge-modal").modal();
  });

  $(".comments-challenge").click(function (_event) {
    $("#challenge-comments-window").modal();
  });
  });

  // Because this JS is shared by a few pages,
  // we should only insert the CommentBox if it's actually in use
  if (document.querySelector("#comment-box")) {
    // Insert CommentBox element
    const commentBox = Vue.extend(CommentBox);
    let vueContainer = document.createElement("div");
    document.querySelector("#comment-box").appendChild(vueContainer);
    new commentBox({
      propsData: { type: "challenge", id: window.CHALLENGE_ID },
    }).$mount(vueContainer);
  }

  $.get("/userchallenge/api/challenges/types", function (res) {
    const data = res.data;
    loadChalTemplate(data["standard"]);

    $("#create-chals-select input[name=type]").change(function () {
      let challenge = data[this.value];
      loadChalTemplate(challenge);
    });
  });
