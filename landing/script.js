// TaloNet landing — small progressive enhancements only.
(function () {
  "use strict";

  var nav = document.getElementById("nav");
  var toggle = document.getElementById("navToggle");

  // Sticky nav background after scroll.
  var onScroll = function () {
    if (window.scrollY > 24) nav.classList.add("is-stuck");
    else nav.classList.remove("is-stuck");
  };
  onScroll();
  window.addEventListener("scroll", onScroll, { passive: true });

  // Mobile menu.
  if (toggle) {
    toggle.addEventListener("click", function () {
      var open = nav.classList.toggle("is-open");
      toggle.setAttribute("aria-expanded", open ? "true" : "false");
    });
    nav.querySelectorAll(".nav__links a").forEach(function (a) {
      a.addEventListener("click", function () {
        nav.classList.remove("is-open");
        toggle.setAttribute("aria-expanded", "false");
      });
    });
  }

  // Reveal section content on scroll.
  var reveals = document.querySelectorAll(".reveal");
  if ("IntersectionObserver" in window) {
    var io = new IntersectionObserver(
      function (entries) {
        entries.forEach(function (e) {
          if (e.isIntersecting) {
            e.target.classList.add("is-in");
            io.unobserve(e.target);
          }
        });
      },
      { threshold: 0.1, rootMargin: "0px 0px -8% 0px" }
    );
    reveals.forEach(function (el) { io.observe(el); });
  } else {
    reveals.forEach(function (el) { el.classList.add("is-in"); });
  }

  // Background clips can be paused by the browser's autoplay policy on some
  // engines; keep them muted+inline and nudge them to play whenever possible.
  var bgVideos = document.querySelectorAll("video.band__media");
  var play = function (v) {
    v.muted = true;                       // muted is required for autoplay
    try { v.setAttribute("muted", ""); } catch (e) {}
    var p = v.play();
    if (p && p.catch) p.catch(function () {});
  };
  var playAll = function () { bgVideos.forEach(play); };
  bgVideos.forEach(function (v) {
    if (v.readyState >= 2) play(v);
    v.addEventListener("loadeddata", function () { play(v); }, { once: true });
    v.addEventListener("canplay", function () { play(v); }, { once: true });
  });
  // Some engines (e.g. iOS Low Power Mode) defer autoplay until a gesture or
  // until the tab is visible again; retry on the first interaction / focus.
  ["touchstart", "pointerdown", "click", "keydown"].forEach(function (ev) {
    window.addEventListener(ev, playAll, { once: true, passive: true });
  });
  document.addEventListener("visibilitychange", function () {
    if (!document.hidden) playAll();
  });

  // Contact form — client-side acknowledgement (no backend).
  var form = document.getElementById("briefForm");
  var ok = document.getElementById("formOk");
  if (form && ok) {
    form.addEventListener("submit", function (ev) {
      ev.preventDefault();
      if (!form.checkValidity()) {
        form.reportValidity();
        return;
      }
      form.querySelectorAll(".field, .form__grid, button, .form__note").forEach(function (el) {
        el.style.display = "none";
      });
      ok.classList.add("is-on");
    });
  }

  // Footer year.
  var y = document.getElementById("year");
  if (y) y.textContent = String(new Date().getFullYear());
})();
