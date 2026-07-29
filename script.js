/* ==========================================================
   BreatheRun Website
   script.js

   Everything here is an enhancement. The `js` class is set in
   each page head, and the hidden-then-revealed states in
   style.css are scoped to it, so with JavaScript off the page
   renders in full rather than as a header and a footer.
   ========================================================== */


/* ==========================================================
   SCROLL REVEAL

   Both .reveal (whole sections) and .fade-up (cards inside a
   section) are driven by the same observer, so a card cannot
   animate while it is still three screens below the fold.
   ========================================================== */

(function () {

    const targets = document.querySelectorAll(".reveal, .fade-up");

    if (!targets.length) {
        return;
    }

    /* Respect the OS setting: show everything, animate nothing. */

    const still = window.matchMedia("(prefers-reduced-motion: reduce)");

    if (still.matches) {

        targets.forEach(el => el.classList.add("active"));

        return;

    }

    const observer = new IntersectionObserver((entries) => {

        entries.forEach(entry => {

            if (!entry.isIntersecting) {
                return;
            }

            entry.target.classList.add("active");

            /* One-shot. Nothing re-hides on the way back up, so
               there is no reason to keep watching. */

            observer.unobserve(entry.target);

        });

    }, {

        threshold: 0.15,

        /* Start a little early so a section is settled by the
           time it is properly in view. */

        rootMargin: "0px 0px -40px 0px"

    });

    targets.forEach(el => observer.observe(el));

})();


/* ==========================================================
   MOBILE NAVIGATION

   The button is only visible below the nav breakpoint; above
   it the list is always shown and the open state is inert, so
   nothing has to be unwound on resize.
   ========================================================== */

(function () {

    const toggle = document.querySelector(".nav-toggle");
    const menu = document.getElementById("primary-nav");

    if (!toggle || !menu) {
        return;
    }

    const icon = toggle.querySelector(".material-symbols-rounded");

    function setOpen(open) {

        toggle.setAttribute("aria-expanded", String(open));

        menu.classList.toggle("is-open", open);

        if (icon) {
            icon.textContent = open ? "close" : "menu";
        }

    }

    toggle.addEventListener("click", () => {

        const open = toggle.getAttribute("aria-expanded") === "true";

        setOpen(!open);

    });

    /* Tapping a link should navigate and close, not leave the
       menu covering the section it just jumped to. */

    menu.addEventListener("click", (e) => {

        if (e.target.closest("a")) {
            setOpen(false);
        }

    });

    document.addEventListener("keydown", (e) => {

        if (e.key === "Escape" &&
            toggle.getAttribute("aria-expanded") === "true") {

            setOpen(false);

            toggle.focus();

        }

    });

})();
