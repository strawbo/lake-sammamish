document.addEventListener("DOMContentLoaded", function () {
    const datasets = [
        {
            label: "Current Year",
            data: dataCurrent.map(row => ({ x: new Date(row.date), y: row.max_temperature_f })),
            borderColor: "rgba(0, 123, 255, 1)",  // More vibrant blue
            backgroundColor: "rgba(0, 123, 255, 0.2)",
            fill: false,
            borderWidth: 3, // Thicker line for current year
            pointRadius: 4, // Make points more visible
            tension: 0.2
        }
    ];
    
    const colors = ["rgba(220, 53, 69, 1)", "rgba(255, 193, 7, 1)", "rgba(40, 167, 69, 1)", "rgba(108, 117, 125, 1)", "rgba(23, 162, 184, 1)"];
    let colorIndex = 0;
    
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
            borderDash: [6, 3], // Dotted lines for past years
            pointRadius: 3,  // Show data points for past years
            fill: false,
            tension: 0.2
        });
        colorIndex++;
    });


    const ctx = document.getElementById("lakeChart").getContext("2d");

    const chartConfig = {
        type: "line",
        data: { datasets: datasets },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                x: {
                    type: "time",
                    time: {
                        unit: "day",
                        tooltipFormat: "MMM d",
                        displayFormats: { day: "MMM d" }
                    },
                    title: { display: true, text: "Date" },
                    ticks: {
                        autoSkip: true,
                        maxTicksLimit: 7 // Prevent overlapping labels
                    },
                    min: new Date(new Date().setDate(new Date().getDate() - 7)),
                    max: new Date(new Date().setDate(new Date().getDate() + 7))
                },
                y: {
                    suggestedMin: 40,
                    suggestedMax: 90,
                    title: { display: true, text: "Temperature (°F)" },
                    grid: {
                        color: "rgba(200, 200, 200, 0.3)" // Lighten gridlines
                    }
                }
            },
            plugins: {
                legend: {
                    position: "top",
                    labels: {
                        usePointStyle: true,
                        font: { size: 14 }
                    }
                },
                tooltip: {
                    callbacks: {
                        label: function(tooltipItem) {
                            return `${tooltipItem.dataset.label}: ${tooltipItem.raw.y}°F`;
                        }
                    }
                }
            }
        }
    };
    
    new Chart(ctx, chartConfig);
});
