// Student-provided preferences live on their Clerk account, never in shared browser storage.
(() => {
  "use strict";
  const limits = {displayName: 80, school: 120, major: 100, graduation: 40, interests: 300, goal: 500};
  function normalize(value) {
    const source = value && typeof value === "object" ? value : {};
    return Object.fromEntries(Object.entries(limits).map(([key, limit]) =>
      [key, typeof source[key] === "string" ? source[key].trim().slice(0, limit) : ""]));
  }

  function mount(clerk, accountName) {
    const account = document.getElementById("profile-account");
    const edit = document.getElementById("profile-edit");
    const form = document.getElementById("profile-editor");
    const save = document.getElementById("profile-save");
    const cancel = document.getElementById("profile-cancel");
    const status = document.getElementById("profile-save-status");
    if (!account || !form || !edit) return;
    const expectedId = account.dataset.clerkUserId;
    const user = () => {
      if (!clerk.session || !clerk.user || clerk.user.id !== expectedId) {
        throw new Error("Your sign-in changed. Reload this page before editing your profile.");
      }
      return clerk.user;
    };
    let profile = normalize(user().unsafeMetadata?.pathfinderProfile);
    let saving = false;

    function render() {
      const name = profile.displayName || accountName || "Your account";
      document.getElementById("profile-name").textContent = name;
      document.getElementById("profile-name-value").textContent = name;
      document.getElementById("profile-avatar").textContent = name.split(/\s+/).slice(0, 2).map(part => part[0]).join("").toUpperCase();
      document.querySelectorAll("[data-profile-field]").forEach(element => {
        element.textContent = profile[element.dataset.profileField] || "Not added yet";
      });
      const tags = document.getElementById("profile-interests");
      tags.replaceChildren();
      const interests = [...new Set(profile.interests.split(",").map(value => value.trim()).filter(Boolean))];
      if (!interests.length) tags.textContent = "No interests added yet";
      interests.forEach(value => {
        const tag = document.createElement("span");
        tag.className = "profile-tag";
        tag.textContent = value;
        tags.appendChild(tag);
      });
    }
    function close() {
      form.hidden = true;
      edit.hidden = false;
      edit.setAttribute("aria-expanded", "false");
      edit.focus();
    }
    edit.addEventListener("click", () => {
      try {
        user();
        Object.keys(limits).forEach(key => { form.elements.namedItem(key).value = profile[key]; });
        status.textContent = "";
        form.hidden = false;
        edit.hidden = true;
        edit.setAttribute("aria-expanded", "true");
        form.elements.namedItem("displayName").focus();
      } catch (error) { status.textContent = error.message; }
    });
    cancel.addEventListener("click", () => { if (!saving) close(); });
    form.addEventListener("submit", async event => {
      event.preventDefault();
      if (saving || !form.reportValidity()) return;
      const values = Object.fromEntries(Object.keys(limits).map(key => [key, form.elements.namedItem(key).value]));
      const next = normalize(values);
      saving = true;
      save.disabled = cancel.disabled = true;
      status.textContent = "Saving profile…";
      try {
        const current = user();
        // update() replaces unsafeMetadata, so preserve unrelated app metadata.
        await current.update({unsafeMetadata: {...current.unsafeMetadata, pathfinderProfile: next}});
        user();
        profile = next;
        render();
        close();
        status.textContent = "Profile saved.";
      } catch (error) {
        status.textContent = error.errors?.[0]?.longMessage || error.message || "Unable to save your profile. Please retry.";
      } finally {
        saving = false;
        save.disabled = cancel.disabled = false;
      }
    });
    render();
    edit.disabled = false;
  }
  if (typeof module !== "undefined" && module.exports) module.exports = {normalize, mount};
  if (typeof window !== "undefined") window.PathfinderProfile = {mount};
})();
