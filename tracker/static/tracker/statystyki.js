if (document.getElementById('wykresAktywnosci')) {
    new Chart(document.getElementById('wykresAktywnosci'), {
        type: 'bar',
        data: {
            labels: JSON.parse(document.getElementById('etykiety-wykresu').textContent).map(function (d) {
                const czesci = d.split('-');
                return czesci[2] + '.' + czesci[1];
            }),
            datasets: [{
                label: 'Liczba ćwiczeń',
                data: JSON.parse(document.getElementById('wartosci-wykresu').textContent),
                backgroundColor: '#2563eb',
                borderRadius: 4,
                maxBarThickness: 24,
            }]
        },
        options: {
            responsive: true,
            plugins: { legend: { display: false } },
            scales: {
                x: { grid: { display: false }, ticks: { color: '#6c757d', maxRotation: 0 } },
                y: {
                    beginAtZero: true,
                    grid: { color: '#e9ecef' },
                    ticks: { color: '#6c757d', precision: 0 },
                },
            }
        }
    });
}

if (document.getElementById('progres-dane')) {
    (function () {
        const dane = JSON.parse(document.getElementById('progres-dane').textContent);
        const NIEBIESKI = '#2563eb';
        const SZARY = '#8a94a0';
        const TUSZ = '#212529';
        const SIATKA = '#e9ecef';
        const TLO = '#ffffff';
        const liczba = function (wartosc) {
            return String(Math.round(wartosc * 10) / 10).replace('.', ',');
        };
        const etykiety = dane.map(function (d) { return d.etykieta; });
        const wartosciRm = dane.map(function (d) { return d.rm; });
        let najwyzszy = -1;
        wartosciRm.forEach(function (w, i) {
            if (w !== null && (najwyzszy === -1 || w >= wartosciRm[najwyzszy])) { najwyzszy = i; }
        });
        let ostatni = -1;
        for (let i = wartosciRm.length - 1; i >= 0; i--) {
            if (wartosciRm[i] !== null) { ostatni = i; break; }
        }
        const kluczowe = [najwyzszy, ostatni];
        const duzoPunktow = dane.length > 40;
        const promienRm = function (kontekst) {
            if (kluczowe.indexOf(kontekst.dataIndex) !== -1) { return 6; }
            return duzoPunktow ? 0 : 5;
        };
        const osX = {
            grid: { display: false },
            ticks: { color: '#6c757d', maxRotation: 0, autoSkip: true, maxTicksLimit: 8 },
        };
        const tooltip = {
            callbacks: {
                title: function (elementy) { return dane[elementy[0].dataIndex].data; },
                afterBody: function (elementy) {
                    const d = dane[elementy[0].dataIndex];
                    const linie = [];
                    if (d.powt_rm !== null) {
                        linie.push('Seria bazowa 1RM: ' + d.powt_rm + ' x ' + liczba(d.ciezar_rm) + ' kg');
                    }
                    linie.push('Najcięższa seria: ' + d.powt_ciezar + ' x ' + liczba(d.ciezar) + ' kg');
                    return linie;
                },
            },
        };

        const wiersze = dane.slice().reverse().map(function (d) {
            const bazowa = d.powt_rm === null ? '-' : d.powt_rm + ' x ' + liczba(d.ciezar_rm) + ' kg';
            const rm = d.rm === null ? '-' : liczba(d.rm) + ' kg';
            return '<tr><td>' + d.data + '</td><td>' + bazowa + '</td><td>' + rm + '</td><td>' +
                d.powt_ciezar + ' x ' + liczba(d.ciezar) + ' kg</td></tr>';
        });
        document.getElementById('tabela-progresu').innerHTML = wiersze.join('');

        const maRm = dane.some(function (d) { return d.rm !== null; });
        if (!maRm) {
            document.getElementById('blok-1rm').style.display = 'none';
            document.getElementById('brak-rm').style.display = 'block';
        }

        const etykietyKluczowe = {
            id: 'etykietyKluczowe',
            afterDatasetsDraw: function (wykres) {
                const indeksy = [];
                if (najwyzszy >= 0) { indeksy.push(najwyzszy); }
                if (ostatni >= 0 && ostatni !== najwyzszy) { indeksy.push(ostatni); }

                const ctx = wykres.ctx;
                const punkty = wykres.getDatasetMeta(0).data;
                ctx.save();
                ctx.font = '600 12px system-ui, -apple-system, "Segoe UI", sans-serif';
                ctx.fillStyle = TUSZ;
                ctx.strokeStyle = TLO;
                ctx.lineWidth = 4;
                ctx.lineJoin = 'round';
                ctx.textAlign = 'center';
                let poprzedniX = null;
                indeksy.sort(function (x, y) { return x - y; }).forEach(function (i) {
                    const d = dane[i];
                    const tekst = liczba(d.rm) + ' kg';
                    const szer = ctx.measureText(tekst).width;
                    const lewy = wykres.chartArea.left + szer / 2;
                    const prawy = wykres.chartArea.right - szer / 2;
                    const x = Math.min(Math.max(punkty[i].x, lewy), prawy);
                    let y = punkty[i].y - 14;
                    if (poprzedniX !== null && Math.abs(x - poprzedniX) < szer + 8) { y = punkty[i].y + 24; }
                    ctx.strokeText(tekst, x, y);
                    ctx.fillText(tekst, x, y);
                    poprzedniX = x;
                });
                ctx.restore();
            },
        };

        if (maRm) {
            new Chart(document.getElementById('wykresProgresu'), {
                type: 'line',
                data: {
                    labels: etykiety,
                    datasets: [
                        {
                            label: 'Szacowane 1RM',
                            data: dane.map(function (d) { return d.rm; }),
                            borderColor: NIEBIESKI,
                            backgroundColor: NIEBIESKI,
                            borderWidth: 3,
                            pointRadius: promienRm,
                            pointHoverRadius: 7,
                            pointBorderColor: TLO,
                            pointBorderWidth: 2,
                            spanGaps: true,
                            tension: 0.15,
                            order: 1,
                        },
                        {
                            label: 'Największy ciężar',
                            data: dane.map(function (d) { return d.ciezar; }),
                            borderColor: SZARY,
                            backgroundColor: SZARY,
                            borderWidth: 2,
                            pointRadius: duzoPunktow ? 0 : 4,
                            pointHoverRadius: 6,
                            pointBorderColor: TLO,
                            pointBorderWidth: 2,
                            tension: 0.15,
                            order: 2,
                        },
                    ]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    interaction: { mode: 'index', intersect: false },
                    layout: { padding: { top: 28, right: 12 } },
                    scales: {
                        x: osX,
                        y: {
                            beginAtZero: false,
                            grace: '12%',
                            grid: { color: SIATKA },
                            ticks: { color: '#6c757d', callback: function (v) { return v + ' kg'; } },
                        },
                    },
                    plugins: {
                        legend: { position: 'bottom', labels: { usePointStyle: true, boxWidth: 8 } },
                        tooltip: tooltip,
                    },
                },
                plugins: [etykietyKluczowe],
            });
        }
    })();
}
