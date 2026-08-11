/* GAAM Doctor UI */

(function initTheme() {
    const saved = localStorage.getItem('doc_dark');

    if (saved === '1') {
        document.documentElement.classList.add('dark');
    }

    updateDarkButton();
})();


function updateDarkButton() {
    const btn = document.getElementById('darkBtn');
    if (!btn) return;

    const dark = document.documentElement.classList.contains('dark');

    btn.innerHTML = dark
        ? '<i class="fa-solid fa-sun"></i>'
        : '<i class="fa-solid fa-moon"></i>';
}


function toggleDark() {
    const dark = document.documentElement.classList.toggle('dark');

    localStorage.setItem('doc_dark', dark ? '1' : '0');

    updateDarkButton();
}


let sidebarOpen = true;


function toggleSidebar() {
    const sidebar = document.getElementById('sidebar');
    const topbar = document.getElementById('topbar');
    const main = document.getElementById('mainArea');
    const overlay = document.getElementById('mobileOverlay');

    if (window.innerWidth <= 900) {
        const opening =
            !sidebar.classList.contains('mobile-open');

        sidebar.classList.toggle('mobile-open', opening);
        overlay.classList.toggle('active', opening);

        return;
    }

    sidebarOpen = !sidebarOpen;

    sidebar.classList.toggle('collapsed', !sidebarOpen);
    topbar.classList.toggle('full', !sidebarOpen);
    main.classList.toggle('full', !sidebarOpen);

    localStorage.setItem(
        'doctor_sidebar_open',
        String(sidebarOpen)
    );
}


function closeMobileSidebar() {
    const sidebar = document.getElementById('sidebar');
    const overlay = document.getElementById('mobileOverlay');

    if (sidebar) {
        sidebar.classList.remove('mobile-open');
    }

    if (overlay) {
        overlay.classList.remove('active');
    }
}


(function restoreSidebar() {
    if (
        localStorage.getItem('doctor_sidebar_open') === 'false' &&
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


function afgTime() {
    const now = new Date();

    const utc =
        now.getTime() +
        now.getTimezoneOffset() * 60000;

    const afg =
        new Date(utc + 4.5 * 3600000);

    const pad =
        value => String(value).padStart(2, '0');

    const time =
        pad(afg.getHours()) + ':' +
        pad(afg.getMinutes()) + ':' +
        pad(afg.getSeconds());

    const date =
        afg.getFullYear() + '/' +
        pad(afg.getMonth() + 1) + '/' +
        pad(afg.getDate());

    const smallClock =
        document.getElementById('afgClock');

    const bigClock =
        document.getElementById('afgClockBig');

    const dateEl =
        document.getElementById('afgDate');

    if (smallClock) {
        smallClock.textContent = time;
    }

    if (bigClock) {
        bigClock.textContent = time;
    }

    if (dateEl) {
        dateEl.textContent = date;
    }
}


setInterval(afgTime, 1000);
afgTime();


function confirmDelete(id, name) {
    const modal =
        document.getElementById('deleteModal');

    const text =
        document.getElementById('deleteModalText');

    const form =
        document.getElementById('deleteForm');

    if (!modal || !text || !form) return;

    text.textContent =
        'حذف رکورد صحی ' + name + ' ؟';

    form.action =
        '/core/doctor/record/' + id + '/delete/';

    modal.classList.add('open');
}


function closeDeleteModal() {
    document.getElementById('deleteModal')
        ?.classList.remove('open');
}


function confirmDeletePresence(id, date) {
    const modal =
        document.getElementById('deletePresenceModal');

    const text =
        document.getElementById('deletePresenceText');

    const form =
        document.getElementById('deletePresenceForm');

    if (!modal || !text || !form) return;

    text.textContent =
        'حذف حضور ' + date + ' ؟';

    form.action =
        '/core/doctor/presence/' + id + '/delete/';

    modal.classList.add('open');
}


function closePresenceModal() {
    document.getElementById('deletePresenceModal')
        ?.classList.remove('open');
}


document
    .querySelectorAll('.modal-overlay')
    .forEach(function (element) {
        element.addEventListener(
            'click',
            function (event) {
                if (event.target === element) {
                    element.classList.remove('open');
                }
            }
        );
    });


document.addEventListener(
    'keydown',
    function (event) {
        if (event.key === 'Escape') {
            closeDeleteModal();
            closePresenceModal();
            closeMobileSidebar();
        }
    }
);


document.addEventListener(
    'DOMContentLoaded',
    function () {

        const today =
            new Date()
                .toISOString()
                .split('T')[0];

        const reportDate =
            document.getElementById('rf_date');

        if (reportDate && !reportDate.value) {
            reportDate.value = today;
        }

        const presenceDate =
            document.getElementById('presence_date');

        if (presenceDate && !presenceDate.value) {
            presenceDate.value = today;
        }


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

    }
);
