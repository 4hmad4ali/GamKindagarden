const header = document.getElementById('site-header');
const progress = document.getElementById('page-progress');

function updateScrollUI() {
    const y = window.scrollY;

    if (header) {
        header.classList.toggle('scrolled', y > 20);
    }

    if (progress) {
        const scrollHeight =
            document.documentElement.scrollHeight -
            document.documentElement.clientHeight;

        const percent =
            scrollHeight > 0
                ? (y / scrollHeight) * 100
                : 0;

        progress.style.width = percent + '%';
    }
}

window.addEventListener(
    'scroll',
    updateScrollUI,
    { passive: true }
);

updateScrollUI();


/* ===============================
   SCROLL REVEAL ANIMATION
================================ */

const revealElements =
    document.querySelectorAll('.reveal');

const observer =
    new IntersectionObserver(
        entries => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    entry.target.classList.add('visible');
                    observer.unobserve(entry.target);
                }
            });
        },
        {
            threshold: 0.15
        }
    );

revealElements.forEach(element => {
    observer.observe(element);
});


/* ===============================
   ANIMATED COUNTERS
================================ */

const counters =
    document.querySelectorAll('[data-counter]');

const counterObserver =
    new IntersectionObserver(
        entries => {
            entries.forEach(entry => {
                if (!entry.isIntersecting) {
                    return;
                }

                const element = entry.target;

                const target =
                    Number(element.dataset.counter || 0);

                const duration = 1100;

                const startTime =
                    performance.now();

                function animate(now) {
                    const progress =
                        Math.min(
                            (now - startTime) / duration,
                            1
                        );

                    const eased =
                        1 - Math.pow(1 - progress, 3);

                    element.textContent =
                        Math.round(target * eased);

                    if (progress < 1) {
                        requestAnimationFrame(animate);
                    }
                }

                requestAnimationFrame(animate);

                counterObserver.unobserve(element);
            });
        },
        {
            threshold: 0.5
        }
    );

counters.forEach(counter => {
    counterObserver.observe(counter);
});