function pole(wiersz, nazwa) {
    return wiersz.querySelector('input[name$="-' + nazwa + '"]');
}
function dodajWiersz(prefiks, powtorzenia, ciezar) {
    const licznik = document.getElementById('id_' + prefiks + '-TOTAL_FORMS');
    const szablon = document.getElementById('szablon-' + prefiks).innerHTML;
    const tabela = document.getElementById('serie-' + prefiks);
    tabela.insertAdjacentHTML('beforeend', szablon.replaceAll('__prefix__', licznik.value));
    licznik.value = parseInt(licznik.value, 10) + 1;
    const wiersz = tabela.lastElementChild;
    const poprzedni = wiersz.previousElementSibling;
    if (powtorzenia === undefined && poprzedni) {
        pole(wiersz, 'powtorzenia').value = pole(poprzedni, 'powtorzenia').value;
        pole(wiersz, 'ciezar').value = pole(poprzedni, 'ciezar').value;
    } else if (powtorzenia !== undefined) {
        pole(wiersz, 'powtorzenia').value = powtorzenia;
        pole(wiersz, 'ciezar').value = ciezar;
    }
    const podpowiedz = document.getElementById('brak-' + prefiks);
    if (podpowiedz) { podpowiedz.remove(); }
    return wiersz;
}
document.querySelectorAll('[data-dodaj-serie]').forEach(function (przycisk) {
    przycisk.addEventListener('click', function () {
        dodajWiersz(przycisk.dataset.dodajSerie);
    });
});
document.querySelectorAll('[data-jak-ostatnio]').forEach(function (przycisk) {
    przycisk.addEventListener('click', function () {
        JSON.parse(przycisk.dataset.serie).forEach(function (seria) {
            dodajWiersz(przycisk.dataset.jakOstatnio, seria[0], seria[1]);
        });
    });
});

function ustawStanUsuniecia(wiersz) {
    const zaznaczenie = pole(wiersz, 'DELETE');
    const przycisk = wiersz.querySelector('[data-przelacz-usuniecie]');
    wiersz.classList.toggle('seria-usunieta', zaznaczenie.checked);
    przycisk.textContent = zaznaczenie.checked ? 'Przywróć' : 'Usuń';
}
document.querySelectorAll('[data-przelacz-usuniecie]').forEach(function (przycisk) {
    ustawStanUsuniecia(przycisk.closest('tr'));
});
document.addEventListener('click', function (zdarzenie) {
    if (zdarzenie.target.matches('[data-usun-wiersz]')) {
        zdarzenie.target.closest('tr').remove();
    }
    if (zdarzenie.target.matches('[data-przelacz-usuniecie]')) {
        const wiersz = zdarzenie.target.closest('tr');
        const zaznaczenie = pole(wiersz, 'DELETE');
        zaznaczenie.checked = !zaznaczenie.checked;
        ustawStanUsuniecia(wiersz);
    }
});

(function () {
    const licznik = document.getElementById('czas-trwania');
    if (!licznik) { return; }
    const start = new Date(licznik.dataset.start).getTime();
    function dwie(liczba) { return String(liczba).padStart(2, '0'); }
    function odswiez() {
        const sekundy = Math.max(0, Math.floor((Date.now() - start) / 1000));
        licznik.textContent = Math.floor(sekundy / 3600) + ':' + dwie(Math.floor(sekundy % 3600 / 60)) + ':' + dwie(sekundy % 60);
    }
    odswiez();
    setInterval(odswiez, 1000);
})();

    const KLUCZ_KONIEC = 'gymapp_przerwa_koniec';
    const KLUCZ_AUTO = 'gymapp_przerwa_auto';
    const KLUCZ_CZAS = 'gymapp_przerwa_czas';
    const wyswietlacz = document.getElementById('przerwa-czas');
    const wybor = document.getElementById('przerwa-sekundy');
    const auto = document.getElementById('przerwa-auto');
    let zegar = null;

    function odczytaj(klucz) {
        try { return localStorage.getItem(klucz); } catch (e) { return null; }
    }
    function zapisz(klucz, wartosc) {
        try { localStorage.setItem(klucz, wartosc); } catch (e) { }
    }
    function usun(klucz) {
        try { localStorage.removeItem(klucz); } catch (e) { }
    }
    function format(sekundy) {
        return Math.floor(sekundy / 60) + ':' + String(sekundy % 60).padStart(2, '0');
    }
    function sygnal() {
        wyswietlacz.classList.add('text-success');
        if (navigator.vibrate) { navigator.vibrate([200, 100, 200]); }
        try {
            const kontekst = new (window.AudioContext || window.webkitAudioContext)();
            const oscylator = kontekst.createOscillator();
            oscylator.frequency.value = 880;
            oscylator.connect(kontekst.destination);
            oscylator.start();
            oscylator.stop(kontekst.currentTime + 0.4);
        } catch (e) { }
    }
    function zatrzymajZegar() {
        if (zegar !== null) { clearInterval(zegar); zegar = null; }
    }
    function odswiez() {
        const koniec = parseInt(odczytaj(KLUCZ_KONIEC) || '0', 10);
        if (!koniec) {
            wyswietlacz.textContent = '0:00';
            zatrzymajZegar();
            return;
        }
        const pozostalo = Math.ceil((koniec - Date.now()) / 1000);
        if (pozostalo <= 0) {
            usun(KLUCZ_KONIEC);
            wyswietlacz.textContent = '0:00';
            zatrzymajZegar();
            if (pozostalo > -10) { sygnal(); }
            return;
        }
        wyswietlacz.classList.remove('text-success');
        wyswietlacz.textContent = format(pozostalo);
    }
    function uruchom() {
        const sekundy = parseInt(wybor.value, 10);
        zapisz(KLUCZ_CZAS, String(sekundy));
        zapisz(KLUCZ_KONIEC, String(Date.now() + sekundy * 1000));
        zatrzymajZegar();
        odswiez();
        zegar = setInterval(odswiez, 500);
    }

    const zapamietanyCzas = odczytaj(KLUCZ_CZAS);
    if (zapamietanyCzas) { wybor.value = zapamietanyCzas; }
    auto.checked = odczytaj(KLUCZ_AUTO) === '1';
    auto.addEventListener('change', function () { zapisz(KLUCZ_AUTO, auto.checked ? '1' : '0'); });
    wybor.addEventListener('change', function () { zapisz(KLUCZ_CZAS, wybor.value); });
    document.getElementById('przerwa-start').addEventListener('click', uruchom);
    document.getElementById('przerwa-stop').addEventListener('click', function () {
        usun(KLUCZ_KONIEC);
        odswiez();
    });
    document.querySelectorAll('[data-formularz-serii]').forEach(function (formularz) {
        formularz.addEventListener('submit', function () {
            if (auto.checked) {
                zapisz(KLUCZ_KONIEC, String(Date.now() + parseInt(wybor.value, 10) * 1000));
            }
        });
    });
    odswiez();
    if (odczytaj(KLUCZ_KONIEC)) { zegar = setInterval(odswiez, 500); }
})();
