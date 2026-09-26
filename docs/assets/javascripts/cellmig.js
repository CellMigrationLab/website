// Cell Migration Lab – small enhancements. The site works without JavaScript;
// this adds click-to-play videos, the gallery lightbox, the publication filter,
// before/after sliders and a few niceties.
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
      burger.addEventListener("keydown", (e) => {
        if (e.key === "Enter" || e.key === " ") { e.preventDefault(); toggle.checked = !toggle.checked; sync(); }
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
      loops.forEach((v) => { v.removeAttribute("autoplay"); v.pause(); v.controls = true; });
      return;
    }
    if (!("IntersectionObserver" in window)) return;
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

  // Publication search and filter
  function initPublications() {
    const form = document.querySelector("[data-cm-filter]");
    if (!form) return;
    const search = form.querySelector("[data-cm-search]");
    const chips = [...form.querySelectorAll("[data-cm-kind]")];
    const count = form.querySelector("[data-cm-count]");
    const items = [...document.querySelectorAll(".cm-pub[data-search]")];
    const years = [...document.querySelectorAll("[data-cm-year]")];
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
      years.forEach((y) => { y.hidden = !y.querySelector(".cm-pub:not([hidden])"); });
      count.textContent = shown === items.length ? `${items.length} publications` : `${shown} of ${items.length} publications`;
    };
    search.addEventListener("input", apply);
    chips.forEach((c) => c.addEventListener("click", () => {
      kind = c.dataset.cmKind;
      chips.forEach((x) => x.classList.toggle("is-active", x === c));
      apply();
    }));
    apply();
  }

  // Before/after image sliders (image analysis page)
  function initCompare() {
    document.querySelectorAll(".cm-compare").forEach((fig) => {
      const imgs = fig.querySelectorAll("img");
      if (imgs.length < 2 || fig.classList.contains("is-ready")) return;
      fig.classList.add("is-ready");
      const range = document.createElement("input");
      range.type = "range"; range.min = "0"; range.max = "100"; range.value = "50";
      range.setAttribute("aria-label", "Compare input and result");
      const handle = document.createElement("span");
      handle.className = "cm-compare__handle";
      const box = imgs[0].closest("p") || fig;
      box.style.position = "relative";
      box.append(handle, range);
      range.addEventListener("input", () => fig.style.setProperty("--pos", range.value + "%"));
    });
  }

  // Preprint lag chart: tooltip on hover / focus / tap
  function initLagChart() {
    const plot = document.querySelector(".cm-lag__plot");
    if (!plot) return;
    const tip = plot.querySelector(".cm-lag__tip");
    const show = (dot) => {
      const box = plot.getBoundingClientRect(), r = dot.getBoundingClientRect();
      tip.textContent = dot.dataset.tip;
      tip.style.left = Math.min(Math.max(r.left + r.width / 2 - box.left, 90), box.width - 90) + "px";
      tip.style.top = (r.top - box.top) + "px";
      tip.hidden = false;
    };
    plot.querySelectorAll(".cm-lag__dot").forEach((dot) => {
      dot.querySelector("title")?.remove();  // our tooltip replaces the browser's
      dot.addEventListener("mouseenter", () => show(dot));
      dot.addEventListener("mouseleave", () => { tip.hidden = true; });
      dot.parentElement.addEventListener("focus", () => show(dot));
      dot.parentElement.addEventListener("blur", () => { tip.hidden = true; });
    });
  }

  function init() {
    initLagChart();
    initHeader();
    initVideos();
    initLoops();
    initLightbox();
    initPublications();
    initCompare();
  }

  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", init);
  else init();
})();
