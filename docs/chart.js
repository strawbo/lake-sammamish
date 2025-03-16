document.addEventListener("DOMContentLoaded", function () {
    const datasets = [
        {
            label: "Current Year",
            data: dataCurrent.map(row => ({ x: new Date(row.date), y: row.max_temperature_f })),
            borderColor: "rgba(0, 123, 255, 1)",
            backgroundColor: "rgba(0, 123, 255, 0.2)",
            fill: false,
            borderWidth: 3,
            pointRadius: 4,
            tension: 0.2
        }
    ];

    const colors = ["rgba(220, 53, 69, 1)", "rgba(255, 193, 7, 1)", "rgba(40, 167, 69, 1)", "rgba(108, 117, 125, 1)", "rgba(23, 162, 184, 1)"];

    // Extract unique years from past data
    const years = Array.from(new Set(dataPast.map(row => row.pYear))); 

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
            borderDash: [6, 3],
            pointRadius: 3,
            fill: false,
            tension: 0.2
        });
        colorIndex++;
    });

    // Define temperature bands
    const temperatureBands = [
        { min: 40, max: 50, color: "rgba(153, 196, 255, 0.3)", label: "Ice Cold" },
        { min: 50, max: 60, color: "rgba(173, 216, 230, 0.3)", label: "Very Cold" },
        { min: 60, max: 68, color: "rgba(144, 238, 144, 0.3)", label: "Chilly" },
        { min: 68, max: 75, color: "rgba(255, 223, 186, 0.3)", label: "Comfortable" },
        { min: 75, max: 80, color: "rgba(255, 165, 0, 0.3)", label: "Perfect" },
        { min: 80, max: 90, color: "rgba(255, 69, 0, 0.3)", label: "Very Warm" }
    ];

    // Plugin to draw temperature bands
    const backgroundBandsPlugin = {
        id: "backgroundBands",
        beforeDraw: (chart) => {
            const { ctx, scales: { y, x } } = chart;
            ctx.save();

            temperatureBands.forEach(band => {
                ctx.fillStyle = band.color;
                ctx.fillRect(x.left, y.getPixelForValue(band.max), x.right - x.left, y.getPixelForValue(band.min) - y.getPixelForValue(band.max));

                // Label inside the band
                ctx.fillStyle = "black";
                ctx.font = "bold 12px Arial";
                ctx.fillText(
                    band.label, 
                    x.left + 10,
                    y.getPixelForValue((band.min + band.max) / 2)
                );
            });

            ctx.restore();
        }
    };

    // Adjust font sizes dynamically based on screen width
    function getResponsiveFontSize() {
        return Math.max(10, Math.min(16, window.innerWidth / 50)); // Adjust range as needed
    }
    
    // Create the chart
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
                    time: {
                        unit: "day",
                        tooltipFormat: "MMM d",
                        displayFormats: { day: "MMM d" }
                    },
                    title: { 
                        display: true, 
                        text: "Date", 
                        font: { size: getResponsiveFontSize() } },
                    ticks: {
                        autoSkip: true,
                        maxTicksLimit: 7,
                        font: { size: getResponsiveFontSize() }
                    },
                    min: new Date(new Date().setDate(new Date().getDate() - 7)),
                    max: new Date(new Date().setDate(new Date().getDate() + 7))
                },
                y: {
                    suggestedMin: 40,
                    suggestedMax: 90,
                    title: {
                        display: true, 
                        text: "Temperature (°F)",
                        font: { size: getResponsiveFontSize() } 
                    },
                    ticks: {
                        font: { size: getResponsiveFontSize() }
                    },                    
                    grid: {
                        color: "rgba(200, 200, 200, 0.3)"
                    }
                }
            },
            plugins: {
                legend: {
                    position: "top",
                    labels: {
                        usePointStyle: true,
                        font: { size: getResponsiveFontSize() }
                    }
                },
                tooltip: {
                    callbacks: {
                        label: function (tooltipItem) {
                            return `${tooltipItem.dataset.label}: ${tooltipItem.raw.y}°F`;
                        }
                    }
                }
            }
        },
        plugins: [backgroundBandsPlugin] 
    });
});
