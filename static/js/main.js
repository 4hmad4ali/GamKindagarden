console.log('GAAM Kindergarten Loaded');
function showSection(id) {
    document.querySelectorAll('.section').forEach(s => s.classList.add('hidden'));
    const s = document.getElementById(id);
    if(s) s.classList.remove('hidden');
}
