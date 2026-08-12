/* =========================================================
   GAAM HOMEPAGE
   UI / UX INTERACTIONS
========================================================= */

'use strict';


/* =========================================================
   DOM
========================================================= */

const header = document.getElementById('site-header');
const progress = document.getElementById('page-progress');

const menuToggle = document.getElementById('menu-toggle');
const mobileMenu = document.getElementById('mobile-menu');

const desktopNavLinks = document.querySelectorAll(
    '.desktop-nav a[href^="#"]'
);

const mobileNavLinks = document.querySelectorAll(
    '#mobile-menu a[href^="#"]'
);

const sectionLinks = document.querySelectorAll(
    'a[href^="#"]:not([href="#"])'
);

const revealElements = document.querySelectorAll('.reveal');

const reduceMotion = window.matchMedia(
    '(prefers-reduced-motion: reduce)'
).matches;


/* =========================================================
   SCROLL STATE
========================================================= */

let ticking = false;


function updateScrollUI() {

    const scrollTop =
        window.scrollY ||
        document.documentElement.scrollTop;

    /*
     * Header glass/background state
     */
    if (header) {
        header.classList.toggle(
            'scrolled',
            scrollTop > 18
        );
    }


    /*
     * Page progress
     */
    if (progress) {

        const documentHeight =
            document.documentElement.scrollHeight;

        const viewportHeight =
            window.innerHeight;

        const available =
            documentHeight - viewportHeight;

        const percentage =
            available > 0
                ? Math.min(
                    Math.max(
                        (scrollTop / available) * 100,
                        0
                    ),
                    100
                )
                : 0;

        progress.style.width =
            `${percentage}%`;
    }

}


function requestScrollUpdate() {

    if (ticking) {
        return;
    }

    ticking = true;

    requestAnimationFrame(() => {

        updateScrollUI();

        ticking = false;

    });

}


window.addEventListener(
    'scroll',
    requestScrollUpdate,
    {
        passive: true
    }
);


window.addEventListener(
    'resize',
    requestScrollUpdate,
    {
        passive: true
    }
);


updateScrollUI();


/* =========================================================
   MOBILE MENU
========================================================= */

function isMobileMenuOpen() {

    return mobileMenu?.classList.contains('open');

}


function openMenu() {

    if (!menuToggle || !mobileMenu) {
        return;
    }

    mobileMenu.classList.add('open');

    mobileMenu.hidden = false;

    mobileMenu.setAttribute(
        'aria-hidden',
        'false'
    );

    menuToggle.classList.add('active');

    menuToggle.setAttribute(
        'aria-expanded',
        'true'
    );

    menuToggle.setAttribute(
        'aria-label',
        'بستن فهرست'
    );

    header?.classList.add('menu-active');

    document.body.classList.add('menu-open');

}


function closeMenu({
    returnFocus = false
} = {}) {

    if (!menuToggle || !mobileMenu) {
        return;
    }

    mobileMenu.classList.remove('open');

    mobileMenu.hidden = true;

    mobileMenu.setAttribute(
        'aria-hidden',
        'true'
    );

    menuToggle.classList.remove('active');

    menuToggle.setAttribute(
        'aria-expanded',
        'false'
    );

    menuToggle.setAttribute(
        'aria-label',
        'باز کردن فهرست'
    );

    header?.classList.remove('menu-active');

    document.body.classList.remove('menu-open');


    if (returnFocus) {
        menuToggle.focus();
    }

}


function toggleMenu() {

    if (isMobileMenuOpen()) {
        closeMenu();
    } else {
        openMenu();
    }

}


if (menuToggle && mobileMenu) {

    menuToggle.addEventListener(
        'click',
        event => {

            event.stopPropagation();

            toggleMenu();

        }
    );


    mobileMenu.addEventListener(
        'click',
        event => {

            /*
             * Prevent clicks inside the menu itself
             * from triggering the outside-click handler.
             */
            event.stopPropagation();

        }
    );


    mobileMenu
        .querySelectorAll('a')
        .forEach(link => {

            link.addEventListener(
                'click',
                () => closeMenu()
            );

        });


    /*
     * Click outside menu
     */
    document.addEventListener(
        'click',
        event => {

            if (!isMobileMenuOpen()) {
                return;
            }

            if (
                !mobileMenu.contains(event.target) &&
                !menuToggle.contains(event.target)
            ) {
                closeMenu();
            }

        }
    );


    /*
     * Keyboard accessibility
     */
    document.addEventListener(
        'keydown',
        event => {

            if (
                event.key === 'Escape' &&
                isMobileMenuOpen()
            ) {

                closeMenu({
                    returnFocus: true
                });

            }

        }
    );


    /*
     * Desktop resize
     */
    window.addEventListener(
        'resize',
        () => {

            if (
                window.innerWidth > 900 &&
                isMobileMenuOpen()
            ) {

                closeMenu();

            }

        },
        {
            passive: true
        }
    );

}


/* =========================================================
   SMOOTH ANCHOR NAVIGATION
========================================================= */

sectionLinks.forEach(link => {

    link.addEventListener(
        'click',
        event => {

            const targetSelector =
                link.getAttribute('href');

            if (
                !targetSelector ||
                targetSelector === '#'
            ) {
                return;
            }

            const target =
                document.querySelector(
                    targetSelector
                );

            if (!target) {
                return;
            }

            event.preventDefault();


            /*
             * Account for fixed header.
             */
            const headerHeight =
                header?.offsetHeight || 70;

            const targetPosition =
                target.getBoundingClientRect().top +
                window.scrollY -
                headerHeight -
                18;


            window.scrollTo({

                top: targetPosition,

                behavior:
                    reduceMotion
                        ? 'auto'
                        : 'smooth'

            });


            /*
             * Update URL without jumping.
             */
            history.replaceState(
                null,
                '',
                targetSelector
            );

        }
    );

});


/* =========================================================
   ACTIVE NAVIGATION / SCROLL SPY
========================================================= */

const sections = [
    'features',
    'experience',
    'roles',
    'contact'
]
    .map(id => document.getElementById(id))
    .filter(Boolean);


function setActiveNavigation(id) {

    [
        ...desktopNavLinks,
        ...mobileNavLinks
    ].forEach(link => {

        const active =
            link.getAttribute('href') ===
            `#${id}`;

        link.classList.toggle(
            'active',
            active
        );


        if (active) {

            link.setAttribute(
                'aria-current',
                'true'
            );

        } else {

            link.removeAttribute(
                'aria-current'
            );

        }

    });

}


if (
    'IntersectionObserver' in window &&
    sections.length
) {

    const navigationObserver =
        new IntersectionObserver(

            entries => {

                /*
                 * Find the most visible section.
                 */
                const visible =
                    entries
                        .filter(
                            entry =>
                                entry.isIntersecting
                        )
                        .sort(
                            (a, b) =>
                                b.intersectionRatio -
                                a.intersectionRatio
                        );

                if (visible.length) {

                    setActiveNavigation(
                        visible[0].target.id
                    );

                }

            },

            {
                rootMargin:
                    '-25% 0px -60% 0px',

                threshold: [
                    0,
                    0.1,
                    0.25,
                    0.5
                ]
            }

        );


    sections.forEach(section => {
        navigationObserver.observe(section);
    });

}


/* =========================================================
   REVEAL ANIMATIONS
========================================================= */

if (reduceMotion) {

    revealElements.forEach(element => {

        element.classList.add('visible');

    });

} else if ('IntersectionObserver' in window) {

    const revealObserver =
        new IntersectionObserver(

            entries => {

                entries.forEach(entry => {

                    if (!entry.isIntersecting) {
                        return;
                    }

                    entry.target.classList.add(
                        'visible'
                    );

                    revealObserver.unobserve(
                        entry.target
                    );

                });

            },

            {
                threshold: 0.1,

                rootMargin:
                    '0px 0px -35px 0px'
            }

        );


    revealElements.forEach(element => {

        revealObserver.observe(element);

    });

} else {

    /*
     * Old browser fallback
     */
    revealElements.forEach(element => {

        element.classList.add('visible');

    });

}


/* =========================================================
   HERO SHOULD NEVER FLASH INVISIBLE
========================================================= */

window.addEventListener(
    'load',
    () => {

        document
            .querySelectorAll(
                '.hero .reveal'
            )
            .forEach(element => {

                element.classList.add(
                    'visible'
                );

            });

    }
);


/* =========================================================
   ESCAPE HASH CORRECTION ON INITIAL LOAD
========================================================= */

window.addEventListener(
    'load',
    () => {

        if (!window.location.hash) {
            return;
        }

        const target =
            document.querySelector(
                window.location.hash
            );

        if (!target) {
            return;
        }

        const headerHeight =
            header?.offsetHeight || 70;

        setTimeout(() => {

            window.scrollTo({

                top:
                    target.offsetTop -
                    headerHeight -
                    18,

                behavior: 'auto'

            });

        }, 0);

    }
);
