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

  // Sideways-scrolling rows (the journal covers). When they all fit, one row
  // and no buttons. Otherwise the row loops: copies of the covers sit on either
  // side, and after a scroll the position jumps by one set of covers back into
  // the middle copy, which looks the same, so there is no end to reach.
  // Copies are hidden from screen readers and keyboards, and a click on one
  // opens the original in the lightbox.
  function initStrips() {
    document.querySelectorAll("[data-cm-strip]").forEach((strip) => {
      const track = strip.querySelector("ul");
      const originals = [...track.children];
      const make = (cls, label, text, dir) => {
        const b = document.createElement("button");
        b.type = "button"; b.className = cls; b.setAttribute("aria-label", label); b.textContent = text;
        b.addEventListener("click", () => track.scrollBy({ left: dir * track.clientWidth * 0.8 }));
        strip.appendChild(b);
        return b;
      };
      const buttons = [make("cm-strip__prev", "Previous covers", "‹", -1),
                       make("cm-strip__next", "Next covers", "›", 1)];
      const copy = (li) => {
        const c = li.cloneNode(true);
        c.setAttribute("aria-hidden", "true");
        c.dataset.cmCopy = "";
        c.querySelectorAll("a").forEach((a) => {
          a.tabIndex = -1;
          a.removeAttribute("data-cm-lightbox");   // the lightbox lists each cover once
          a.addEventListener("click", (ev) => { ev.preventDefault(); li.querySelector("a").click(); });
        });
        return c;
      };
      let set = 0;   // width of one set of covers, gap included; 0 when they all fit
      const jump = (by) => {
        track.style.scrollBehavior = "auto";
        track.scrollLeft += by;
        track.style.scrollBehavior = "";
      };
      const layout = () => {
        const at = set ? track.scrollLeft - set : 0;
        track.querySelectorAll("[data-cm-copy]").forEach((c) => c.remove());
        set = 0;
        const fits = track.scrollWidth <= track.clientWidth + 2;
        buttons.forEach((b) => { b.hidden = fits; });
        if (fits) return;
        track.prepend(...originals.map(copy));
        track.append(...originals.map(copy));
        set = originals[0].offsetLeft - track.children[0].offsetLeft;
        jump(set + at - track.scrollLeft);
      };
      let settle;
      track.addEventListener("scroll", () => {
        clearTimeout(settle);
        settle = setTimeout(() => {   // once the scroll has stopped: back into the middle copy
          if (!set) return;
          if (track.scrollLeft < set * 0.5) jump(set);
          else if (track.scrollLeft >= set * 1.5) jump(-set);
        }, 150);
      }, { passive: true });
      let resized;
      window.addEventListener("resize", () => { clearTimeout(resized); resized = setTimeout(layout, 150); });
      layout();
    });
  }

  // Gallery: full rows stretch to the page width, but the last row is not full
  // and would stay at its smaller starting size. Give it the height of the row
  // above, so every row matches (the flex growth set by the build is the
  // picture's aspect ratio times 100, the first number of its inline flex).
  function initGalleryRows() {
    document.querySelectorAll("ul.cm-gallery").forEach((list) => {
      const items = [...list.children];
      const flex = items.map((li) => li.style.flex);   // as built: "<ratio × 100> 1 <basis>"
      const layout = () => {
        items.forEach((li, i) => { li.style.flex = flex[i]; });
        const lastTop = items[items.length - 1].offsetTop;
        const last = items.filter((li) => li.offsetTop === lastTop);
        const above = items.filter((li) => li.offsetTop < lastTop).pop();
        if (!above) return;   // one row: nothing to match
        const height = above.getBoundingClientRect().height;
        last.forEach((li) => {
          const ratio = parseFloat(flex[items.indexOf(li)]) / 100;
          li.style.flex = `0 1 ${ratio * height}px`;
        });
      };
      let resized;
      window.addEventListener("resize", () => { clearTimeout(resized); resized = setTimeout(layout, 150); });
      layout();
    });
  }

  // Email links: without a mail app a mailto: link does nothing, so a click
  // also copies the address and says so (the mail app still opens if there is one)
  function initMailCopy() {
    const note = document.createElement("div");
    note.className = "cm-toast";
    note.setAttribute("role", "status");
    note.hidden = true;
    document.body.appendChild(note);
    let timer;
    document.addEventListener("click", (ev) => {
      const a = ev.target.closest && ev.target.closest('a[href^="mailto:"]');
      if (!a) return;
      const address = decodeURIComponent(a.getAttribute("href").slice(7).split("?")[0]);
      const show = (text) => {
        note.textContent = text;
        note.hidden = false;
        clearTimeout(timer);
        timer = setTimeout(() => { note.hidden = true; }, 4000);
      };
      // Where copying is not allowed, the note still shows the address
      const copied = navigator.clipboard ? navigator.clipboard.writeText(address) : Promise.reject();
      copied.then(() => show(`Copied ${address}`), () => show(`Email: ${address}`));
    });
  }

  // Gallery lightbox (arrow keys, swipe, Escape)
  function initLightbox() {
    const links = [...document.querySelectorAll("a[data-cm-lightbox]")];
    if (!links.length || typeof HTMLDialogElement === "undefined") return;
    const dialog = document.createElement("dialog");
    dialog.className = "cm-lightbox";
    dialog.setAttribute("aria-label", "Image viewer");
    dialog.innerHTML =
      '<figure><img alt=""><video controls playsinline loop hidden></video><figcaption></figcaption></figure>' +
      '<button class="cm-lightbox__close" type="button" aria-label="Close">×</button>' +
      '<button class="cm-lightbox__prev" type="button" aria-label="Previous image">‹</button>' +
      '<button class="cm-lightbox__next" type="button" aria-label="Next image">›</button>';
    document.body.appendChild(dialog);
    const img = dialog.querySelector("img");
    const video = dialog.querySelector("video");
    const cap = dialog.querySelector("figcaption");
    let index = 0;
    // An item with data-cm-video (a gallery video) opens in the player, the others as an image.
    const show = (i) => {
      index = (i + links.length) % links.length;
      const a = links[index];
      const isVideo = "cmVideo" in a.dataset;
      img.hidden = isVideo;
      video.hidden = !isVideo;
      video.pause();
      if (isVideo) {
        video.src = a.href;
        video.setAttribute("aria-label", a.dataset.caption || "");
        video.play().catch(() => {});
      } else {
        video.removeAttribute("src");
        img.src = a.href;
        img.alt = a.dataset.caption || "";
      }
      cap.textContent = a.dataset.caption || "";
    };
    links.forEach((a, i) => a.addEventListener("click", (e) => { e.preventDefault(); show(i); dialog.showModal(); }));
    dialog.querySelector(".cm-lightbox__close").addEventListener("click", () => dialog.close());
    dialog.addEventListener("close", () => video.pause());
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
    initStrips();
    initGalleryRows();
    initMailCopy();
    initLightbox();
    initFilter();
  }

  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", init);
  else init();
})();
