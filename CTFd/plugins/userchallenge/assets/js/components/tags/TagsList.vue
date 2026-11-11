<template>
  <div class="col-md-12">
    <div id="challenge-tags" class="my-3">
      <span
        class="badge badge-primary mx-1 challenge-tag"
        v-for="tag in tags"
        :key="tag.id"
      >
        <span>{{ tag.value }}</span>
        <a class="btn-fa delete-tag" @click="deleteTag(tag.id)"> &#215;</a>
      </span>
    </div>

    <div class="form-group">
      <label for="tags-add-input">Tag</label>
      <select
        id="tags-add-input"
        class="form-control"
        v-model="tagValue"
        @change="newTagValue = tagValue === '__new__' ? '' : newTagValue"
      >
        <option value="" disabled>Select a tag</option>
        <option value="__new__">Add a new tag...</option>
        <option
          v-for="tag in availableTags"
          :key="tag.value"
          :value="tag.value"
          :disabled="isTagSelected(tag.value)"
        >
          {{ tag.value }}
        </option>
      </select>
      <input
        v-if="tagValue === '__new__'"
        id="new-tag-input"
        maxlength="80"
        type="text"
        class="form-control mt-2"
        placeholder="Enter a new tag"
        v-model.trim="newTagValue"
        @keyup.enter="setTag()"
      />
      <button
        type="button"
        class="btn btn-primary mt-2"
        :disabled="!tagToSet"
        @click="setTag()"
      >
        Set tag
      </button>
    </div>
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
      tags: [],
      availableTags: [],
      tagValue: "",
      newTagValue: "",
    };
  },
  methods: {
    loadAvailableTags: function () {
      CTFd.fetch("/userchallenge/api/tags", {
        method: "GET",
      })
        .then((response) => {
          return response.json();
        })
        .then((response) => {
          if (response.success) {
            this.availableTags = response.data;
          }
        });
    },
    isTagSelected: function (value) {
      return this.tags.some((tag) => tag.value === value);
    },
    loadTags: function () {
      CTFd.fetch(`/userchallenge/api/challenges/${this.$props.challenge_id}/tags`, {
        method: "GET",
        credentials: "same-origin",
        headers: {
          Accept: "application/json",
          "Content-Type": "application/json",
        },
      })
        .then((response) => {
          return response.json();
        })
        .then((response) => {
          if (response.success) {
            this.tags = response.data;
          }
        });
    },
    setTag: function () {
      if (!this.tagToSet) {
        return;
      }

      const params = {
        value: this.tagToSet,
        challenge: this.$props.challenge_id,
      };
      CTFd.fetch("/userchallenge/api/tags", {
        method: "POST",
        body: JSON.stringify(params),
      })
        .then((response) => {
          return response.json();
        })
        .then((response) => {
          if (response.success) {
            this.tagValue = "";
            this.newTagValue = "";
            this.loadTags();
            this.loadAvailableTags();
          }
        });
    },
    deleteTag: function (tag_id) {
      CTFd.api.delete_tag({ tagId: tag_id }).then((response) => {
        if (response.success) {
          this.loadTags();
        }
      });
    },
  },
  computed: {
    tagToSet: function () {
      if (this.tagValue === "__new__") {
        return this.newTagValue;
      }
      return this.tagValue;
    },
  },
  created() {
    this.loadTags();
    this.loadAvailableTags();
  },
};
</script>

<style scoped></style>
