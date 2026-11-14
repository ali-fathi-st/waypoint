/**
 * Profile (profile.html): one form for who you are, what you're looking
 * for, your skills, experience and education. Saving recalculates every
 * job's match score.
 *
 * Repeatable rows (skills, roles, schools) are copied from the <template>
 * elements at the bottom of profile.html.
 */
import { initShell } from "../ui/shell.js";
import { api } from "../api/api.js";
import { describeError, isApiError } from "../api/errors.js";
import { $, $$, render, withBusy } from "../lib/dom.js";
import { icon } from "../ui/icons.js";
import { toast } from "../ui/toast.js";
import { createTagInput } from "../ui/tag-input.js";
import { errorState, loadingBlock } from "../ui/states.js";
import { formatDateTime } from "../lib/format.js";

initShell();
for (const id of ["#add-skill", "#add-experience", "#add-education"])
  $(id).prepend(icon("plus"));

const form = $("#profile-form");
let profile = null; // last saved version
let baseline = ""; // collect() of the saved version, to detect unsaved changes
let rowCounter = 0;

const titles = createTagInput($("#titles"), {
  inputId: "titles-input",
  placeholder: "Data Engineer",
  describedBy: "titles-hint titles-error",
  onChange: updateSaveBar,
});
const locations = createTagInput($("#locations"), {
  inputId: "locations-input",
  placeholder: "Edmonton, AB",
  describedBy: "locations-hint",
  onChange: updateSaveBar,
});
const exclusions = createTagInput($("#exclusions"), {
  inputId: "exclusions-input",
  placeholder: "Senior",
  describedBy: "exclusions-hint",
  onChange: updateSaveBar,
});

// =============================================================== rows

/** Copy a <template>, give its fields unique ids, fill in values. */
function addRow(kind, values = {}) {
  const fragment = $(`#${kind}-template`).content.cloneNode(true);
  const row = fragment.firstElementChild;
  const n = ++rowCounter;
  row.dataset.id = values.id ?? `${kind}_${Date.now().toString(36)}${n}`;

  for (const input of row.querySelectorAll("[data-field]")) {
    const field = input.dataset.field;
    const id = `${kind}-${n}-${field}`;
    input.id = id;
    const label = row.querySelector(`[data-label="${field}"]`);
    if (label) label.htmlFor = id;
    const error = row.querySelector(`[data-error="${field}"]`);
    if (error) {
      error.id = `${id}-error`;
      input.setAttribute("aria-describedby", error.id);
    }
    const value = values[field];
    if (input.type === "checkbox") input.checked = Boolean(value);
    else input.value = value ?? input.value ?? "";
  }

  const remove = row.querySelector("[data-remove]");
  if (remove.classList.contains("btn--icon")) remove.append(icon("trash"));
  else remove.prepend(icon("trash"));
  remove.addEventListener("click", () => {
    row.remove();
    updateSaveBar();
  });

  $(`#${kind === "skill" ? "skills" : kind}`).append(row);
  return row;
}

function rowValues(kind) {
  return $$(`[data-row="${kind}"]`).map((row) => {
    const values = { id: row.dataset.id };
    for (const input of row.querySelectorAll("[data-field]")) {
      values[input.dataset.field] =
        input.type === "checkbox" ? input.checked : input.value.trim();
    }
    return values;
  });
}

// =============================================================== read / write the form

function numberOrNull(value) {
  return value === "" ? null : Number(value);
}

/** Everything in the form, in the shape the API expects. */
function collect() {
  return {
    full_name: form.elements.full_name.value.trim(),
    email: form.elements.email.value.trim(),
    headline: form.elements.headline.value.trim(),
    summary: form.elements.summary.value.trim(),
    preferred_titles: titles.getValues(),
    locations: locations.getValues(),
    exclusions: exclusions.getValues(),
    work_arrangements: $$('input[name="arrangement"]:checked').map(
      (c) => c.value,
    ),
    salary_min: numberOrNull(form.elements.salary_min.value),
    salary_max: numberOrNull(form.elements.salary_max.value),
    salary_currency: form.elements.salary_currency.value,
    skills: rowValues("skill").map(({ name, proficiency, years }) => ({
      name,
      proficiency,
      years: numberOrNull(years),
    })),
    experience: rowValues("experience").map((e) => ({
      ...e,
      end_month: e.end_month || null,
    })),
    education: rowValues("education").map((e) => ({
      ...e,
      field: e.field || null,
      end_month: e.end_month || null,
    })),
  };
}

function fill(p) {
  form.elements.full_name.value = p.full_name;
  form.elements.email.value = p.email;
  form.elements.headline.value = p.headline;
  form.elements.summary.value = p.summary;
  titles.setValues(p.preferred_titles);
  locations.setValues(p.locations);
  exclusions.setValues(p.exclusions);
  for (const box of $$('input[name="arrangement"]'))
    box.checked = p.work_arrangements.includes(box.value);
  form.elements.salary_min.value = p.salary_min ?? "";
  form.elements.salary_max.value = p.salary_max ?? "";
  form.elements.salary_currency.value = p.salary_currency;
  render($("#skills"));
  render($("#experience"));
  render($("#education"));
  p.skills.forEach((s) => addRow("skill", s));
  p.experience.forEach((e) => addRow("experience", e));
  p.education.forEach((e) => addRow("education", e));
  clearErrors();
  baseline = JSON.stringify(collect());
  updateSaveBar();
}

// =============================================================== validation

function clearErrors() {
  for (const el of $$(".field__error", form)) el.hidden = true;
  for (const el of $$("[aria-invalid]", form))
    el.removeAttribute("aria-invalid");
}

/** Mark one field as wrong. `target` is the input (or the tag box). */
function flag(errorId, message, target) {
  const error = document.getElementById(errorId);
  error.textContent = message;
  error.hidden = false;
  target?.setAttribute("aria-invalid", "true");
}

/** Returns the elements with problems (empty array = valid). */
function validate(values) {
  clearErrors();
  const problems = [];
  const need = (ok, errorId, message, target) => {
    if (!ok) {
      flag(errorId, message, target);
      problems.push(target);
    }
  };

  need(
    values.full_name,
    "full_name-error",
    "Enter your name.",
    form.elements.full_name,
  );
  need(
    /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(values.email),
    "email-error",
    "Enter a valid email address.",
    form.elements.email,
  );
  need(
    values.preferred_titles.length,
    "titles-error",
    "Add at least one target title.",
    $("#titles"),
  );
  need(
    values.work_arrangements.length,
    "arrangements-error",
    "Choose at least one.",
    $('input[name="arrangement"]'),
  );
  need(
    values.salary_min === null ||
      values.salary_max === null ||
      values.salary_max >= values.salary_min,
    "salary_max-error",
    "Must be at least the starting salary.",
    form.elements.salary_max,
  );

  for (const row of $$('[data-row="skill"]')) {
    const input = row.querySelector('[data-field="name"]');
    need(
      input.value.trim(),
      `${input.id}-error`,
      "Name the skill, or remove the row.",
      input,
    );
  }
  for (const row of $$('[data-row="experience"]')) {
    const field = (name) => row.querySelector(`[data-field="${name}"]`);
    need(
      field("title").value.trim(),
      `${field("title").id}-error`,
      "Enter a job title.",
      field("title"),
    );
    need(
      field("company").value.trim(),
      `${field("company").id}-error`,
      "Enter the employer.",
      field("company"),
    );
    need(
      field("start_month").value,
      `${field("start_month").id}-error`,
      "Enter the start month.",
      field("start_month"),
    );
    const start = field("start_month").value;
    const end = field("end_month").value;
    need(
      !end || !start || end >= start,
      `${field("end_month").id}-error`,
      "The end is before the start.",
      field("end_month"),
    );
  }
  for (const row of $$('[data-row="education"]')) {
    const field = (name) => row.querySelector(`[data-field="${name}"]`);
    need(
      field("institution").value.trim(),
      `${field("institution").id}-error`,
      "Enter the institution.",
      field("institution"),
    );
    need(
      field("credential").value.trim(),
      `${field("credential").id}-error`,
      "Enter the credential.",
      field("credential"),
    );
  }
  return problems.filter(Boolean);
}

// =============================================================== save bar

function updateSaveBar() {
  if (!profile) return;
  const dirty = JSON.stringify(collect()) !== baseline;
  $("#save").disabled = !dirty;
  $("#discard").disabled = !dirty;
  $("#save-status").textContent = dirty
    ? "You have unsaved changes"
    : `Saved ${formatDateTime(profile.updated_at)}`;
}

form.addEventListener("input", updateSaveBar);
form.addEventListener("change", updateSaveBar);
$("#discard").addEventListener("click", () => fill(profile));
$("#add-skill").addEventListener("click", () => {
  addRow("skill").querySelector("input").focus();
  updateSaveBar();
});
$("#add-experience").addEventListener("click", () => {
  addRow("experience").querySelector("input").focus();
  updateSaveBar();
});
$("#add-education").addEventListener("click", () => {
  addRow("education").querySelector("input").focus();
  updateSaveBar();
});

form.addEventListener("submit", async (e) => {
  e.preventDefault();
  const values = collect();
  const problems = validate(values);
  if (problems.length) {
    $("#save-status").textContent =
      `${problems.length} ${problems.length === 1 ? "field needs" : "fields need"} attention`;
    (problems[0].querySelector?.("input") ?? problems[0]).focus();
    return;
  }
  await withBusy($("#save"), "Saving...", async () => {
    try {
      profile = await api.updateCandidateProfile(values);
      fill(profile);
      toast.success("Profile saved", "Match scores were recalculated.");
    } catch (err) {
      toast.error("Couldn't save your profile", describeError(err));
    }
  });
  updateSaveBar();
});

// Warn before leaving with unsaved changes.
window.addEventListener("beforeunload", (e) => {
  if (profile && JSON.stringify(collect()) !== baseline) e.preventDefault();
});

// =============================================================== load

async function load() {
  render($("#error"), loadingBlock());
  try {
    profile = await api.getCandidateProfile();
    render($("#error"));
    form.hidden = false;
    fill(profile);
  } catch (error) {
    form.hidden = true;
    render($("#error"), errorState(error, load));
    if (!isApiError(error)) console.error(error);
  }
}

load();
