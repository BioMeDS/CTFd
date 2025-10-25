import $ from "jquery";
import CTFd from "./compat/CTFd";
import { ezAlert, ezQuery } from "./compat/ezq";
import "./compat/json";
import "./main";

function deleteSelectedUsers(_event) {
  let userIDs = $("input[data-user-id]:checked").map(function () {
    return $(this).data("user-id");
  });
  let target = userIDs.length === 1 ? "user" : "users";

  ezQuery({
    title: "Delete Users",
    body: `Are you sure you want to delete ${userIDs.length} ${target}?`,
    success: function () {
      const reqs = [];
      for (var userID of userIDs) {
        reqs.push(
          CTFd.fetch(`/api/v1/users/${userID}`, {
            method: "DELETE",
          }),
        );
      }
      Promise.all(reqs).then((_responses) => {
        window.location.reload();
      });
    },
  });
}

function bulkEditUsers(_event) {
  let userIDs = $("input[data-user-id]:checked").map(function () {
    return $(this).data("user-id");
  });

  ezAlert({
    title: "Edit Users",
    body: $(`
    <form id="users-bulk-edit">
      <div class="form-group">
        <label>Verified</label>
        <select name="verified" data-initial="">
          <option value="">--</option>
          <option value="true">True</option>
          <option value="false">False</option>
        </select>
      </div>
      <div class="form-group">
        <label>Banned</label>
        <select name="banned" data-initial="">
          <option value="">--</option>
          <option value="true">True</option>
          <option value="false">False</option>
        </select>
      </div>
      <div class="form-group">
        <label>Hidden</label>
        <select name="hidden" data-initial="">
          <option value="">--</option>
          <option value="true">True</option>
          <option value="false">False</option>
        </select>
      </div>
      <div class ="form-group">
      <label>Email Notif</label>
        <select name="notifications" data-initial="">
          <option value="">--</option>
          <option value="true">Enabled</option>
          <option value="false">Disabled</option>
        </select>
      </div>
    </form>
    `),
    button: "Submit",
    success: function () {
      let data = $("#users-bulk-edit").serializeJSON(true);
      const reqs = [];
      for (var userID of userIDs) {
        reqs.push(
          CTFd.fetch(`/api/v1/users/${userID}`, {
            method: "PATCH",
            body: JSON.stringify(data),
          }),
        );
      }
      Promise.all(reqs).then((_responses) => {
        window.location.reload();
      });
    },
  });
}

$(() => {
  $("#users-delete-button").click(deleteSelectedUsers);
  $("#users-edit-button").click(bulkEditUsers);
});
