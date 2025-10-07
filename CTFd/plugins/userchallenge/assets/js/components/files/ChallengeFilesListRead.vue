<template>
  <div>
    <table id="filesboard" class="table table-striped">
      <thead>
        <tr>
          <td class="text-center"><b>File</b></td>
          <td class="text-center"><b>Settings</b></td>
        </tr>
      </thead>
      <tbody>
        <tr v-for="file in files" :key="file.id">
          <td class="text-center">
            <a :href="`${urlRoot}/files/${file.location}`">{{
              file.location.split("/").pop()
            }}</a>
          </td>
        </tr>
      </tbody>
    </table>
  </div>
</template>

<script>
import CTFd from "../../compat/CTFd";

export default {
  props: {
    challenge_id: Number,
  },
  data: function () {
    return {
      files: [],
      urlRoot: CTFd.config.urlRoot,
    };
  },
  methods: {
    loadFiles: function () {
      CTFd.fetch(`/userchallenge/api/challenges/${this.$props.challenge_id}/files`, {
        method: "GET",
      })
        .then((response) => {
          return response.json();
        })
        .then((response) => {
          if (response.success) {
            this.files = response.data;
          }
        });
    }
  },
  created() {
    this.loadFiles();
  },
};
</script>

<style scoped></style>
