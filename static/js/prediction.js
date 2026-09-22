/*
 * static/js/prediction.js
 * --------------------------
 * Client-side validation for the prediction form. This is a
 * convenience layer only — app.py performs the same range checks
 * again on the server, since client-side validation can always be
 * bypassed.
 */

document.addEventListener("DOMContentLoaded", function () {
  var form = document.getElementById("predictionForm");
  if (!form) return;

  form.addEventListener("submit", function (event) {
    var isValid = true;

    form.querySelectorAll("input[type=number]").forEach(function (input) {
      input.classList.remove("is-invalid");

      var value = parseFloat(input.value);
      var min = input.min !== "" ? parseFloat(input.min) : null;
      var max = input.max !== "" ? parseFloat(input.max) : null;

      var outOfRange =
        input.value === "" ||
        isNaN(value) ||
        (min !== null && value < min) ||
        (max !== null && value > max);

      if (outOfRange) {
        input.classList.add("is-invalid");
        isValid = false;
      }
    });

    form.querySelectorAll("input[required][type=text]").forEach(function (input) {
      input.classList.remove("is-invalid");
      if (!input.value.trim()) {
        input.classList.add("is-invalid");
        isValid = false;
      }
    });

    if (!isValid) {
      event.preventDefault();
      var firstInvalid = form.querySelector(".is-invalid");
      if (firstInvalid) {
        firstInvalid.scrollIntoView({ behavior: "smooth", block: "center" });
        firstInvalid.focus();
      }
    }
  });
});
