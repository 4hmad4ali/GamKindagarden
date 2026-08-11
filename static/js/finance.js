/* GAAM Finance UI */

(function initTheme() {
    if (localStorage.getItem('fin_dark') === 'true') {
        document.documentElement.classList.add('dark');
    }

    updateDarkButton();
})();


function updateDarkButton() {
    const btn = document.getElementById('darkBtn');

    if (!btn) return;

    const dark =
        document.documentElement.classList.contains('dark');

    btn.innerHTML = dark
        ? '<i class="fa-solid fa-sun"></i>'
        : '<i class="fa-solid fa-moon"></i>';
}


function toggleDark() {
    const dark =
        document.documentElement.classList.toggle('dark');

    localStorage.setItem(
        'fin_dark',
        String(dark)
    );

    updateDarkButton();
}


let sidebarOpen = true;


function toggleSidebar() {
    const sidebar =
        document.getElementById('sidebar');

    const topbar =
        document.getElementById('topbar');

    const main =
        document.getElementById('mainArea');

    const overlay =
        document.getElementById('mobileOverlay');

    if (window.innerWidth <= 900) {
        const opening =
            !sidebar.classList.contains('mobile-open');

        sidebar.classList.toggle(
            'mobile-open',
            opening
        );

        overlay.classList.toggle(
            'active',
            opening
        );

        return;
    }

    sidebarOpen = !sidebarOpen;

    sidebar.classList.toggle(
        'collapsed',
        !sidebarOpen
    );

    topbar.classList.toggle(
        'full',
        !sidebarOpen
    );

    main.classList.toggle(
        'full',
        !sidebarOpen
    );

    localStorage.setItem(
        'fin_sb',
        String(sidebarOpen)
    );
}


function closeMobileSidebar() {
    document.getElementById('sidebar')
        ?.classList.remove('mobile-open');

    document.getElementById('mobileOverlay')
        ?.classList.remove('active');
}


(function restoreSidebar() {
    if (
        localStorage.getItem('fin_sb') === 'false' &&
        window.innerWidth > 900
    ) {
        sidebarOpen = false;

        document.getElementById('sidebar')
            ?.classList.add('collapsed');

        document.getElementById('topbar')
            ?.classList.add('full');

        document.getElementById('mainArea')
            ?.classList.add('full');
    }
})();


function updateFinanceClock() {
    const now = new Date();

    const utc =
        now.getTime() +
        now.getTimezoneOffset() * 60000;

    const kabul =
        new Date(utc + 4.5 * 3600000);

    const pad =
        value => String(value).padStart(2, '0');

    const text =
        pad(kabul.getHours()) + ':' +
        pad(kabul.getMinutes()) + ':' +
        pad(kabul.getSeconds());

    const clock =
        document.getElementById('financeClock');

    if (clock) {
        clock.textContent = text;
    }
}


setInterval(updateFinanceClock, 1000);
updateFinanceClock();


let deleteForm = null;


function openConfirmModal(form) {
    deleteForm = form;

    document.getElementById('confirmModal')
        ?.classList.add('open');
}


function closeConfirmModal() {
    document.getElementById('confirmModal')
        ?.classList.remove('open');

    deleteForm = null;
}


function confirmDeleteSubmit() {
    if (deleteForm) {
        deleteForm.submit();
    }

    closeConfirmModal();
}


document.addEventListener(
    'DOMContentLoaded',
    function () {

        document
            .querySelectorAll('.btn-delete')
            .forEach(function (button) {

                button.addEventListener(
                    'click',
                    function (event) {

                        event.preventDefault();
                        event.stopPropagation();

                        const form =
                            this.closest('form');

                        if (form) {
                            openConfirmModal(form);
                        }

                    }
                );

            });


        document
            .querySelectorAll('.num-field')
            .forEach(function (input) {

                input.addEventListener(
                    'input',
                    function () {
                        this.value =
                            this.value.replace(
                                /[^0-9.]/g,
                                ''
                            );
                    }
                );

            });


        const today =
            new Date()
                .toISOString()
                .split('T')[0];

        document
            .querySelectorAll('.today-field')
            .forEach(function (input) {
                if (!input.value) {
                    input.value = today;
                }
            });

    }
);


document
    .getElementById('confirmModal')
    ?.addEventListener(
        'click',
        function (event) {
            if (event.target === this) {
                closeConfirmModal();
            }
        }
    );


document.addEventListener(
    'keydown',
    function (event) {
        if (event.key === 'Escape') {
            closeConfirmModal();
            closeMobileSidebar();
        }
    }
);
