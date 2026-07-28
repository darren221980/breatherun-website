const observer = new IntersectionObserver((entries) => {

    entries.forEach(entry => {

        if (entry.isIntersecting) {

            entry.target.classList.add("active");

        }

    });

}, {

    threshold:0.15

});

document.querySelectorAll(".reveal").forEach(section => {

    observer.observe(section);

});