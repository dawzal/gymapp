(function () {
    const okno = document.getElementById('okno-czatu');
    const formularz = document.getElementById('formularz-czatu');
    const pole = document.getElementById('pole-tresci');
    const przycisk = document.getElementById('przycisk-wyslij');
    const uzyjDanych = document.getElementById('uzyj-danych');
    const pozostalo = document.getElementById('pozostalo');

    function dodaj(rola, tekst) {
        const powitanie = document.getElementById('powitanie');
        if (powitanie && rola === 'user') { powitanie.remove(); }
        const babelek = document.createElement('div');
        babelek.className = 'babelek babelek-' + rola;
        babelek.textContent = tekst;
        okno.appendChild(babelek);
        okno.scrollTop = okno.scrollHeight;
        return babelek;
    }
    okno.scrollTop = okno.scrollHeight;

    document.querySelectorAll('[data-podpowiedz]').forEach(function (przyciskPodpowiedzi) {
        przyciskPodpowiedzi.addEventListener('click', function () {
            pole.value = przyciskPodpowiedzi.dataset.podpowiedz;
            pole.focus();
        });
    });

    pole.addEventListener('keydown', function (zdarzenie) {
        if (zdarzenie.key === 'Enter' && !zdarzenie.shiftKey) {
            zdarzenie.preventDefault();
            formularz.requestSubmit();
        }
    });

    formularz.addEventListener('submit', async function (zdarzenie) {
        zdarzenie.preventDefault();
        const tresc = pole.value.trim();
        if (!tresc || przycisk.disabled) { return; }
        dodaj('user', tresc);
        pole.value = '';
        const oczekiwanie = dodaj('assistant', 'Asystent pisze...');
        oczekiwanie.classList.add('text-muted');
        przycisk.disabled = true;
        try {
            const odpowiedz = await fetch(formularz.dataset.urlWyslij, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json', 'X-CSRFToken': formularz.dataset.csrf },
                body: JSON.stringify({ tresc: tresc, uzyj_danych: uzyjDanych.checked }),
            });
            const dane = await odpowiedz.json();
            oczekiwanie.classList.remove('text-muted');
            if (odpowiedz.ok) {
                oczekiwanie.textContent = dane.odpowiedz;
                pozostalo.textContent = dane.pozostalo;
            } else {
                oczekiwanie.textContent = dane.blad || 'Wystąpił błąd. Spróbuj ponownie.';
                oczekiwanie.classList.add('text-danger');
                pole.value = tresc;
            }
        } catch (blad) {
            oczekiwanie.classList.remove('text-muted');
            oczekiwanie.classList.add('text-danger');
            oczekiwanie.textContent = 'Brak połączenia z serwerem. Spróbuj ponownie.';
            pole.value = tresc;
        } finally {
            przycisk.disabled = false;
            okno.scrollTop = okno.scrollHeight;
            pole.focus();
        }
    });
})();
