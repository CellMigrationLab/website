// Cell Migration Lab – small enhancements. The site works without JavaScript;
// this adds click-to-play videos, the gallery lightbox, the publication filter
// and a few niceties.
(function () {
  "use strict";

  const reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  // Header gets a hairline once the page is scrolled
  function initHeader() {
    const header = document.querySelector(".cm-header");
    if (!header) return;
    const onScroll = () => header.classList.toggle("is-scrolled", window.scrollY > 8);
    window.addEventListener("scroll", onScroll, { passive: true });
    onScroll();
    const toggle = document.getElementById("cm-menu");
    const burger = document.querySelector(".cm-burger");
    if (toggle && burger) {
      const sync = () => burger.setAttribute("aria-expanded", toggle.checked ? "true" : "false");
      toggle.addEventListener("change", sync);
      // Space opens the menu here; Enter already works (the theme turns Enter on a
      // focused label into a click), so handling it too would toggle twice.
      burger.addEventListener("keydown", (e) => {
        if (e.key === " ") { e.preventDefault(); toggle.checked = !toggle.checked; sync(); }
      });
      document.addEventListener("keydown", (e) => {
        if (e.key === "Escape" && toggle.checked) { toggle.checked = false; sync(); burger.focus(); }
      });
      sync();
    }
  }

  // YouTube / Vimeo: nothing is loaded from the video site until the visitor clicks
  function initVideos() {
    document.querySelectorAll(".cm-video[data-embed]").forEach((box) => {
      const link = box.querySelector("a");
      if (!link) return;
      link.addEventListener("click", (e) => {
        e.preventDefault();
        const iframe = document.createElement("iframe");
        iframe.src = box.dataset.embed;
        iframe.title = link.getAttribute("aria-label") || "Video";
        iframe.allow = "accelerometer; autoplay; encrypted-media; gyroscope; picture-in-picture; fullscreen";
        iframe.allowFullscreen = true;
        box.replaceChildren(iframe);
        iframe.focus();
      });
    });
  }

  // Looping microscopy videos (old GIFs): play only when visible, never with reduced motion
  function initLoops() {
    const loops = document.querySelectorAll("video.cm-loop");
    if (!loops.length) return;
    if (reduceMotion) {
      loops.forEach((v) => { v.pause(); v.controls = true; });
      return;
    }
    if (!("IntersectionObserver" in window)) {   // old browsers: just play (the HTML has no autoplay)
      loops.forEach((v) => v.play().catch(() => {}));
      return;
    }
    const io = new IntersectionObserver((entries) => {
      entries.forEach((en) => {
        if (en.isIntersecting) en.target.play().catch(() => {});
        else en.target.pause();
      });
    }, { rootMargin: "100px" });
    loops.forEach((v) => io.observe(v));
  }

  // Gallery lightbox (arrow keys, swipe, Escape)
  function initLightbox() {
    const links = [...document.querySelectorAll("a[data-cm-lightbox]")];
    if (!links.length || typeof HTMLDialogElement === "undefined") return;
    const dialog = document.createElement("dialog");
    dialog.className = "cm-lightbox";
    dialog.setAttribute("aria-label", "Image viewer");
    dialog.innerHTML =
      '<figure><img alt=""><figcaption></figcaption></figure>' +
      '<button class="cm-lightbox__close" type="button" aria-label="Close">×</button>' +
      '<button class="cm-lightbox__prev" type="button" aria-label="Previous image">‹</button>' +
      '<button class="cm-lightbox__next" type="button" aria-label="Next image">›</button>';
    document.body.appendChild(dialog);
    const img = dialog.querySelector("img");
    const cap = dialog.querySelector("figcaption");
    let index = 0;
    const show = (i) => {
      index = (i + links.length) % links.length;
      const a = links[index];
      img.src = a.href;
      img.alt = a.dataset.caption || "";
      cap.textContent = a.dataset.caption || "";
    };
    links.forEach((a, i) => a.addEventListener("click", (e) => { e.preventDefault(); show(i); dialog.showModal(); }));
    dialog.querySelector(".cm-lightbox__close").addEventListener("click", () => dialog.close());
    dialog.querySelector(".cm-lightbox__prev").addEventListener("click", () => show(index - 1));
    dialog.querySelector(".cm-lightbox__next").addEventListener("click", () => show(index + 1));
    dialog.addEventListener("click", (e) => { if (e.target === dialog || e.target.tagName === "FIGURE") dialog.close(); });
    dialog.addEventListener("keydown", (e) => {
      if (e.key === "ArrowLeft") show(index - 1);
      if (e.key === "ArrowRight") show(index + 1);
    });
    let x0 = null;
    dialog.addEventListener("touchstart", (e) => { x0 = e.touches[0].clientX; }, { passive: true });
    dialog.addEventListener("touchend", (e) => {
      if (x0 === null) return;
      const dx = e.changedTouches[0].clientX - x0;
      if (Math.abs(dx) > 40) show(index + (dx < 0 ? 1 : -1));
      x0 = null;
    });
  }

  // Search (and optional kind chips) over a list: Publications and Datasets.
  // Items carry data-search (lower-case text) and, with chips, data-kind; a
  // [data-cm-group] section (a year, a data type) hides when none of its items shows.
  function initFilter() {
    const form = document.querySelector("[data-cm-filter]");
    if (!form) return;
    const search = form.querySelector("[data-cm-search]");
    const chips = [...form.querySelectorAll("[data-cm-kind]")];
    const count = form.querySelector("[data-cm-count]");
    const noun = form.dataset.cmFilter;
    const items = [...document.querySelectorAll("[data-search]")];
    const groups = [...document.querySelectorAll("[data-cm-group]")];
    let kind = "";
    const params = new URLSearchParams(location.search);
    if (params.get("q")) search.value = params.get("q");
    const apply = () => {
      const words = search.value.toLowerCase().split(/\s+/).filter(Boolean);
      let shown = 0;
      items.forEach((li) => {
        const ok = (!kind || li.dataset.kind === kind) && words.every((w) => li.dataset.search.includes(w));
        li.hidden = !ok;
        if (ok) shown++;
      });
      groups.forEach((g) => { g.hidden = !g.querySelector("[data-search]:not([hidden])"); });
      count.textContent = shown === items.length ? `${items.length} ${noun}` : `${shown} of ${items.length} ${noun}`;
    };
    search.addEventListener("input", apply);
    chips.forEach((c) => c.addEventListener("click", () => {
      kind = c.dataset.cmKind;
      chips.forEach((x) => x.classList.toggle("is-active", x === c));
      apply();
    }));
    apply();
  }

  // Tooltips on the charts and the map (Lab in numbers): hover, focus or tap
  function initChartTips() {
    document.querySelectorAll(".cm-lag__plot, .cm-bars, .cm-map").forEach((box) => {
      const tip = box.querySelector(".cm-chart-tip");
      if (!tip) return;
      const show = (el) => {
        const b = box.getBoundingClientRect(), r = el.getBoundingClientRect();
        tip.textContent = el.dataset.tip;
        tip.style.left = Math.min(Math.max(r.left + r.width / 2 - b.left, 90), b.width - 90) + "px";
        tip.style.top = (r.top - b.top) + "px";
        tip.hidden = false;
      };
      box.querySelectorAll("[data-tip]").forEach((el) => {
        el.querySelector("title")?.remove();  // our tooltip replaces the browser's
        const target = el.closest("a") || el;
        el.addEventListener("mouseenter", () => show(el));
        el.addEventListener("mouseleave", () => { tip.hidden = true; });
        target.addEventListener("focus", () => show(el));
        target.addEventListener("blur", () => { tip.hidden = true; });
      });
    });
  }

  function init() {
    initChartTips();
    initHeader();
    initVideos();
    initLoops();
    initLightbox();
    initFilter();
  }

  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", init);
  else init();
})();
