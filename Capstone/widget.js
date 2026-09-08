/*
 * widget.js -- the embeddable loader. One <script> tag, no dependencies, no build step.
 * Reads its own ?id= and derives the API base from its own src, so it works from any
 * origin without hardcoding a domain.
 *
 * FlyRank Internship capstone -- Embeddable Widget & Lead-Capture Platform.
 */
(function () {
  "use strict";

  var currentScript = document.currentScript;
  if (!currentScript) return;

  var scriptUrl = new URL(currentScript.src);
  var apiBase = scriptUrl.origin;
  var widgetId = scriptUrl.searchParams.get("id");
  if (!widgetId) {
    console.error("[widget.js] missing ?id= on the script tag -- nothing to render");
    return;
  }

  fetch(apiBase + "/widgets/" + widgetId + "/config")
    .then(function (res) {
      if (!res.ok) throw new Error("config fetch failed: " + res.status);
      return res.json();
    })
    .then(function (config) {
      render(config);
    })
    .catch(function (err) {
      console.error("[widget.js] could not load widget config:", err);
    });

  function render(config) {
    var container = document.createElement("div");
    container.className = "flyrank-widget flyrank-widget-" + config.type;
    container.style.cssText =
      "max-width:360px;border:1px solid #ddd;border-radius:8px;padding:16px;font-family:sans-serif;";

    var title = document.createElement("h3");
    title.textContent = config.title;
    title.style.marginTop = "0";
    container.appendChild(title);

    if (config.description) {
      var desc = document.createElement("p");
      desc.textContent = config.description;
      desc.style.cssText = "font-size:14px;color:#555;";
      container.appendChild(desc);
    }

    var form = document.createElement("form");
    var inputs = {};

    (config.fields || []).forEach(function (field) {
      var label = document.createElement("label");
      label.textContent = field.label + (field.required ? " *" : "");
      label.style.cssText = "display:block;margin-top:8px;font-size:13px;";

      var input = document.createElement("input");
      input.type = field.name === "email" ? "email" : "text";
      input.name = field.name;
      input.required = !!field.required;
      input.style.cssText = "display:block;width:100%;box-sizing:border-box;padding:6px;margin-top:4px;";

      inputs[field.name] = input;
      label.appendChild(input);
      form.appendChild(label);
    });

    // Honeypot: a field real visitors never see or fill, positioned off-screen rather
    // than display:none (some bots skip hidden fields, few skip off-screen ones).
    var honeypot = document.createElement("input");
    honeypot.type = "text";
    honeypot.name = "_hp";
    honeypot.tabIndex = -1;
    honeypot.autocomplete = "off";
    honeypot.style.cssText = "position:absolute;left:-9999px;top:-9999px;";
    form.appendChild(honeypot);

    var submitBtn = document.createElement("button");
    submitBtn.type = "submit";
    submitBtn.textContent = config.button_text || "Submit";
    submitBtn.style.cssText = "margin-top:12px;padding:8px 16px;cursor:pointer;";
    form.appendChild(submitBtn);

    var status = document.createElement("p");
    status.style.cssText = "font-size:13px;margin-top:8px;";
    form.appendChild(status);

    form.addEventListener("submit", function (event) {
      event.preventDefault();
      var data = {};
      Object.keys(inputs).forEach(function (name) {
        data[name] = inputs[name].value;
      });

      submitBtn.disabled = true;
      status.textContent = "Sending...";

      fetch(apiBase + "/submissions", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          widget_id: parseInt(widgetId, 10),
          data: data,
          honeypot: honeypot.value,
        }),
      })
        .then(function (res) {
          if (!res.ok) return res.json().then(function (b) { throw new Error(b.error || "submission failed"); });
          return res.json();
        })
        .then(function () {
          status.textContent = "Thanks! We got it.";
          form.reset();
          submitBtn.disabled = false;
        })
        .catch(function (err) {
          status.textContent = "Something went wrong: " + err.message;
          submitBtn.disabled = false;
        });
    });

    container.appendChild(form);
    currentScript.parentNode.insertBefore(container, currentScript.nextSibling);
  }
})();
