const tabela = document.getElementById('cwiczenia-planu');
const komunikat = document.getElementById('komunikat-kolejnosc');
Sortable.create(tabela, {
    handle: '.uchwyt',
    animation: 150,
    onEnd: function () {
        const identyfikatory = Array.from(tabela.querySelectorAll('tr')).map(function (wiersz) {
            return parseInt(wiersz.dataset.id, 10);
        });
        fetch(tabela.dataset.urlKolejnosc, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': tabela.dataset.csrf
            },
            body: JSON.stringify({ kolejnosc: identyfikatory })
        }).then(function (odpowiedz) {
            if (!odpowiedz.ok) { throw new Error('blad'); }
            komunikat.textContent = 'Kolejność zapisana.';
        }).catch(function () {
            komunikat.textContent = 'Nie udało się zapisać kolejności. Odśwież stronę.';
        });
    }
});
