(function () {
  var COOKIE = "bi_demo_who";
  var MAX_AGE = 30 * 24 * 3600;

  function getCookie(name) {
    var parts = ("; " + document.cookie).split("; " + name + "=");
    if (parts.length === 2) {
      return decodeURIComponent(parts.pop().split(";").shift() || "");
    }
    return "";
  }

  function setCookie(value) {
    document.cookie =
      COOKIE +
      "=" +
      encodeURIComponent(value) +
      "; path=/; max-age=" +
      MAX_AGE +
      "; SameSite=Lax";
  }

  function boot() {
    if (getCookie(COOKIE) || document.getElementById("visitor-intro")) {
      return;
    }

    var root = document.createElement("div");
    root.id = "visitor-intro";
    root.className = "visitor-intro";
    root.setAttribute("role", "dialog");
    root.setAttribute("aria-modal", "true");
    root.setAttribute("aria-labelledby", "visitor-intro-title");
    root.innerHTML =
      '<div class="visitor-intro-card">' +
      '  <button type="button" class="visitor-intro-x" aria-label="Dismiss" data-action="skip">&times;</button>' +
      '  <p class="visitor-intro-eyebrow">Optional hello</p>' +
      '  <h2 id="visitor-intro-title">Who\'s visiting?</h2>' +
      '  <p class="visitor-intro-lede">Curious who\'s poking around this portfolio demo. Totally skippable. No spam, no account.</p>' +
      '  <form id="visitor-intro-form" class="visitor-intro-form">' +
      '    <label for="visitor-company">Company <span class="optional">(optional)</span></label>' +
      '    <input id="visitor-company" name="company" type="text" autocomplete="organization" maxlength="120" placeholder="Acme Corp" />' +
      '    <label for="visitor-role">Role <span class="optional">(optional)</span></label>' +
      '    <select id="visitor-role" name="role">' +
      '      <option value="">Select one</option>' +
      '      <option>Recruiter</option>' +
      '      <option>Hiring manager</option>' +
      '      <option>Engineer</option>' +
      '      <option>Analyst</option>' +
      '      <option>Other</option>' +
      '      <option>Prefer not to say</option>' +
      "    </select>" +
      '    <label for="visitor-found">How did you find this? <span class="optional">(optional)</span></label>' +
      '    <select id="visitor-found" name="found_via">' +
      '      <option value="">Select one</option>' +
      "      <option>Resume</option>" +
      "      <option>GitHub</option>" +
      "      <option>Referral</option>" +
      "      <option>Other</option>" +
      "    </select>" +
      '    <div class="visitor-intro-actions">' +
      '      <button type="submit" class="btn">Submit</button>' +
      '      <button type="button" class="btn-secondary" data-action="skip">Skip for now</button>' +
      "    </div>" +
      "  </form>" +
      '  <p class="visitor-intro-privacy">Optional, for this portfolio demo only. Answers show up anonymously on Platform Adoption.</p>' +
      "</div>";

    document.body.appendChild(root);

    function close() {
      root.classList.add("is-gone");
      window.setTimeout(function () {
        if (root.parentNode) {
          root.parentNode.removeChild(root);
        }
      }, 180);
    }

    function post(payload) {
      return fetch("/api/visitor-intro", {
        method: "POST",
        headers: { "Content-Type": "application/json", Accept: "application/json" },
        credentials: "same-origin",
        body: JSON.stringify(payload),
      }).catch(function () {
        return null;
      });
    }

    function skip() {
      setCookie("skipped");
      post({ skipped: true });
      close();
    }

    root.addEventListener("click", function (ev) {
      var t = ev.target;
      if (t === root) {
        skip();
        return;
      }
      if (t && t.getAttribute && t.getAttribute("data-action") === "skip") {
        ev.preventDefault();
        skip();
      }
    });

    var form = document.getElementById("visitor-intro-form");
    if (form) {
      form.addEventListener("submit", function (ev) {
        ev.preventDefault();
        var company = (document.getElementById("visitor-company") || {}).value || "";
        var role = (document.getElementById("visitor-role") || {}).value || "";
        var found = (document.getElementById("visitor-found") || {}).value || "";
        setCookie("answered");
        post({
          skipped: false,
          company: company.trim(),
          role: role,
          found_via: found,
        });
        close();
      });
    }
  }

  if (document.body) {
    boot();
  } else {
    document.addEventListener("DOMContentLoaded", boot);
  }
})();
