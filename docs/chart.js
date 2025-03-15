document.addEventListener("DOMContentLoaded", function () {
    const ctx = document.getElementById("lakeChart").getContext("2d");
    const datasets = [
        {
            label: "Current Year",
            data: dataCurrent.map(row => ({ x: new Date(row.date), y: row.max_temperature_f })),
            borderColor: "rgba(75, 192, 192, 1)",
            backgroundColor: "rgba(75, 192, 192, 0.2)",
            fill: false,
            borderWidth: 5,
            tension: 0.1
        }
    ];

    const colors = ["rgba(192, 75, 75, 1)", "rgba(192, 192, 75, 1)", "rgba(75, 75, 192, 1)", "rgba(192, 75, 192, 1)", "rgba(75, 192, 75, 1)"];
    let colorIndex = 0;

    const years = Array.from(new Set(dataPast.map(row => Math.round(row.pYear))));

    years.forEach(year => {
        const filteredData = dataPast.filter(item => item.pYear === year);
        datasets.push({
            label: `${year}`,
            data: filteredData.map(row => {
                let pastDate = new Date(row.date);
                pastDate.setFullYear(new Date().getFullYear());
                return { x: pastDate, y: row.max_temperature_f };
            }),
            borderColor: colors[colorIndex % colors.length],
            borderWidth: 2,
            borderDash: [5, 5],
            fill: false,
            tension: 0.1
        });
        colorIndex++;
    });

    const ctx = document.getElementById("lakeChart").getContext("2d");

    new Chart(ctx, {
        type: "line",
        data: { datasets: datasets },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                x: {
                    type: "time",
                    time: { unit: "day", tooltipFormat: "MMM d", displayFormats: { day: "MMM d" } },
                    title: { display: true, text: "Date" },
                    min: new Date(new Date().setDate(new Date().getDate() - 7)),
                    max: new Date(new Date().setDate(new Date().getDate() + 7))
                },
                y: {
                    suggestedMin: 40,
                    suggestedMax: 90,
                    title: { display: true, text: "Temperature (°F)" }
                }
            }
        }
    });
});
