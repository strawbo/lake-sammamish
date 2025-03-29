document.addEventListener("DOMContentLoaded", function () {
    const datasets = [
        {
            label: "Current Year",
            data: dataCurrent.map(row => ({ x: new Date(row.date), y: row.max_temperature_f })),
            borderColor: "rgba(0, 123, 255, 1)",
            backgroundColor: "rgba(0, 123, 255, 0.2)",
            fill: false,
            borderWidth: 5,
            pointRadius: 4,
            tension: 0.2
        }
    ];

    // Extract unique years from past data
    const years = Array.from(new Set(dataPast.map(row => row.pYear))); 
    
    const latestYear = Math.max(...dataPast.map(row => row.pYear)); // Find the most recent past year
    years.sort((a, b) => b - a); // Ensure years are in descending order (2024, 2023, ... 2020)
    years.forEach((year, index) => {
        const filteredData = dataPast.filter(item => item.pYear === year);
    
        // Calculate grayscale dynamically: 0 = black, 255 = white
        let grayValue = Math.round((index / (years.length - 1)) * 200); // Keep range from black to light gray
        let color = `rgb(${grayValue}, ${grayValue}, ${grayValue})`;
    
        datasets.push({
            label: `${year}`,
            data: filteredData.map(row => {
                let pastDate = new Date(row.date);
                pastDate.setFullYear(new Date().getFullYear());
                return { x: pastDate, y: row.max_temperature_f };
            }),
            borderColor: color,
            borderWidth: 1,
            borderDash: [6, 3], // Dotted lines for past years
            pointRadius: 3,
            fill: false,
            tension: 0.2
        });
    });

    const chartTitle = document.getElementById("tempDescription");

    if (!chartTitle) {
        console.error("Error: <h2 id='tempDescription'> not found in the HTML.");
        return;
    }

    // Get the current date in Pacific Time
    const now = new Date();
    const todayPacificStr = new Intl.DateTimeFormat("en-US", {
        timeZone: "America/Los_Angeles",
        year: "numeric",
        month: "2-digit",
        day: "2-digit"
    }).format(now);

    // Convert to YYYY-MM-DD format (match dataset)
    const [month, day, year] = todayPacificStr.split("/");
    const todayStr = `${year}-${month.padStart(2, "0")}-${day.padStart(2, "0")}`;
    
    console.log("Pacific Time Today's Date:", todayStr);
    console.log("DataCurrent:", dataCurrent);
    
    // Find today's temperature in dataCurrent
    const todayTempEntry = dataCurrent.find(entry => entry.date.startsWith(todayStr));
    console.log("Today's Temp Entry:", todayTempEntry);
    
    const todayTemp = todayTempEntry ? todayTempEntry.max_temperature_f : null;

    // Extract today's MM-DD for lookup
    const todayMonthDay = todayStr.slice(5);  // Extract "MM-DD" part from "YYYY-MM-DD"
    
    // Find matching past temperatures for today’s date
    const pastTempsForToday = dataPast.filter(entry => entry.date.slice(5, 10) === todayMonthDay);
    
    console.log("Past Temps for Today:", pastTempsForToday)
    
    // Compute average past temperature safely
    const pastAvgTemp = pastTempsForToday.length
        ? (pastTempsForToday.reduce((sum, entry) => sum + Number(entry.max_temperature_f), 0) / pastTempsForToday.length).toFixed(1)
        : null;

    console.log("Past Average Temp:", pastAvgTemp);

    let comparisonText = "";
    if (todayTemp !== null && pastAvgTemp !== null) {
        const tempDiff = (todayTemp - pastAvgTemp).toFixed(1);
        if (tempDiff > 0) {
            comparisonText = `${tempDiff}°F warmer than usual`;
        } else if (tempDiff < 0) {
            comparisonText = `${Math.abs(tempDiff)}°F colder than usual`;
        } else {
            comparisonText = `About average temperature`;
        }
    }

    // Function to format date as "MM/DD at HH:mm"
    function formatTimestamp(date) {
        const options = { month: "2-digit", day: "2-digit", hour: "2-digit", minute: "2-digit", hour12: true };
        return new Intl.DateTimeFormat("en-US", options).format(date);
    }
    
    // Get the latest timestamp from dataCurrent (assumes last entry is most recent)
    const latestEntry = dataCurrent[dataCurrent.length - 1]; // Last recorded temperature
    const latestTimestamp = latestEntry ? new Date(latestEntry.date) : new Date();
    
    // Set the timestamp in the HTML
    document.getElementById("last-updated").innerText = `As of ${formatTimestamp(latestTimestamp)}`;

    
    // Set the title with the computed values
    chartTitle.innerText = `${comparisonText} (${todayTemp}°F)`;


    // Define temperature bands
    const temperatureBands = [
        { min: 40, max: 50, color: "rgba(133, 176, 255, 0.3)", label: "Ice Cold (below 50)" },
        { min: 50, max: 60, color: "rgba(173, 216, 230, 0.3)", label: "Very Cold (50-60)" },
        { min: 60, max: 68, color: "rgba(144, 238, 144, 0.3)", label: "Chilly (60-68)" },
        { min: 68, max: 75, color: "rgba(255, 223, 186, 0.3)", label: "Comfortable (68-75)" },
        { min: 75, max: 80, color: "rgba(255, 165, 0, 0.3)", label: "Perfect (75-80)" },
        { min: 80, max: 90, color: "rgba(255, 69, 0, 0.3)", label: "Very Warm (above 80)" }
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
                ctx.font = `${Math.max(16, Math.min(36, window.innerWidth / 50))}px Arial`; // Adjust font size dynamically
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
        return Math.max(16, Math.min(36, window.innerWidth / 50)); // Adjust range as needed
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
                     title: { display: false}, 
                     ticks: { display: false},
                     grid: { display: false},
                     min: new Date(new Date().setDate(new Date().getDate() - 7)),
                     max: new Date(new Date().setDate(new Date().getDate() + 7))
                },
                y: {
                     suggestedMin: 40,
                     suggestedMax: 90,
                     title: { display: false } ,
                     ticks: { display: false },                    
                     grid: { display: false }
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
