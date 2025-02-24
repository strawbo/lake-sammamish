const SUPABASE_URL = "https://your-supabase-url.supabase.co";
const SUPABASE_KEY = "your-anon-key";

async function fetchData() {
    const response = await fetch(`${SUPABASE_URL}/rest/v1/lake_data?select=date,temperature_c`, {
        headers: {
            "apikey": SUPABASE_KEY,
            "Authorization": `Bearer ${SUPABASE_KEY}`
        }
    });

    const data = await response.json();
    
    // Convert temperature to Fahrenheit
    data.forEach(item => {
        item.temperature_f = (item.temperature_c * 9/5) + 32;
    });

    return data;
}

// Function to render chart using Chart.js
async function renderChart() {
    const data = await fetchData();
    
    const ctx = document.getElementById("lakeChart").getContext("2d");

    const chart = new Chart(ctx, {
        type: "line",
        data: {
            labels: data.map(item => new Date(item.date)),
            datasets: [{
                label: "Water Temperature (°F)",
                data: data.map(item => item.temperature_f),
                borderColor: "rgba(75, 192, 192, 1)",
                borderWidth: 2,
                fill: false
            }]
        },
        options: {
            scales: {
                x: { type: "time", time: { unit: "day" } },
                y: { beginAtZero: false, suggestedMin: 50, suggestedMax: 90 }
            }
        }
    });
}

document.addEventListener("DOMContentLoaded", renderChart);

