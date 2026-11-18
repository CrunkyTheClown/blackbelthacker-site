// TODO: replace this mailto submit with a real form handler.
(function () {
  var form = document.querySelector("[data-scope-form]");
  if (!form) return;

  var fields = [
    ["name", "Enter your name."],
    ["email", "Enter a work email."],
    ["company", "Enter the company name."],
    ["website", "Enter the company website."],
    ["tier", "Select an engagement."],
    ["size", "Enter an approximate size."],
    ["when", "Enter a preferred timeframe."]
  ];

  function show(id, message) {
    var el = document.getElementById(id);
    if (!el) return;
    el.hidden = !message;
    el.textContent = message || "";
  }

  form.addEventListener("submit", function (event) {
    event.preventDefault();
    var ok = true;
    var firstBad = null;
    fields.forEach(function (pair) {
      var input = form.elements[pair[0]];
      var value = (input && input.value || "").trim();
      var bad = !value;
      if (pair[0] === "email" && value && !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(value)) bad = true;
      input.setAttribute("aria-invalid", bad ? "true" : "false");
      show("err-" + pair[0], bad ? pair[1] : "");
      if (bad) {
        ok = false;
        if (!firstBad) firstBad = input;
      }
    });
    var box = form.elements.authorized;
    var boxBad = !box.checked;
    box.setAttribute("aria-invalid", boxBad ? "true" : "false");
    show("err-authorized", boxBad ? "Confirm you are authorized to request this test." : "");
    if (boxBad) {
      ok = false;
      if (!firstBad) firstBad = box;
    }
    var summary = document.getElementById("form-errors");
    summary.hidden = ok;
    summary.textContent = ok ? "" : "Fix the marked fields before sending.";
    if (!ok) {
      if (firstBad && firstBad.focus) firstBad.focus();
      else summary.focus();
      return;
    }
    var lines = [
      "Name: " + form.elements.name.value.trim(),
      "Work email: " + form.elements.email.value.trim(),
      "Company: " + form.elements.company.value.trim(),
      "Website: " + form.elements.website.value.trim(),
      "Engagement: " + form.elements.tier.options[form.elements.tier.selectedIndex].text,
      "Approx size: " + form.elements.size.value.trim(),
      "Timeframe: " + form.elements.when.value.trim(),
      "Notes: " + form.elements.notes.value.trim(),
      "Authorized: yes"
    ];
    window.location.href = "mailto:n0auth@blackbelthacker.com?subject="
      + encodeURIComponent("Scoping request")
      + "&body=" + encodeURIComponent(lines.join("\n"));
  });
})();
