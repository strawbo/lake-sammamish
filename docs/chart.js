document.addEventListener("DOMContentLoaded", function () {

    // --- Score explanation ---
    function getScoreExplanation(c) {
        const snapshot = c.input_snapshot || {};
        const factors = [];

        if (c.water_temp_score != null) {
            const val = snapshot.water_temp_f != null ? Math.round(snapshot.water_temp_f) + "\u00B0F water" : "cold water";
            factors.push({ score: c.water_temp_score, text: val });
        }
        if (c.air_temp_score != null) {
            const val = snapshot.feels_like_f != null ? Math.round(snapshot.feels_like_f) + "\u00B0F air" : "cold air";
            factors.push({ score: c.air_temp_score, text: val });
        }
        if (c.wind_score != null) {
            const val = snapshot.wind_mph != null ? Math.round(snapshot.wind_mph) + " mph wind" : "high wind";
            factors.push({ score: c.wind_score, text: val });
        }
        if (c.sun_score != null) {
            factors.push({ score: c.sun_score, text: "low sun" });
        }
        if (c.rain_score != null) {
            const val = snapshot.precip_pct != null ? Math.round(snapshot.precip_pct) + "% rain chance" : "rain likely";
            factors.push({ score: c.rain_score, text: val });
        }
        if (c.clarity_score != null && c.clarity_score < 60) {
            factors.push({ score: c.clarity_score, text: "murky water" });
        }
        if (c.algae_score != null && c.algae_score < 60) {
            factors.push({ score: c.algae_score, text: "algae concern" });
        }
        if (c.aqi_score != null && c.aqi_score < 60) {
            factors.push({ score: c.aqi_score, text: "poor air quality" });
        }

        const weak = factors.filter(f => f.score < 50).sort((a, b) => a.score - b.score);

        if (weak.length === 0) {
            if (c.overall_score >= 80) return "Great conditions for swimming!";
            const mild = factors.filter(f => f.score < 70).sort((a, b) => a.score - b.score);
            if (mild.length > 0) return "Held back by " + mild.slice(0, 2).map(f => f.text).join(" and ");
            return "";
        }

        const top = weak.slice(0, 3);
        return "Mainly due to " + top.map(f => f.text).join(", ");
    }

    // --- Timestamp ---
    function renderTimestamp() {
        const el = document.getElementById("last-updated");
        if (!el || !dataCurrent || dataCurrent.length === 0) return;

        const latestEntry = dataCurrent[dataCurrent.length - 1];
        const latestTimestamp = new Date(latestEntry.date);
        const options = { month: "numeric", day: "numeric", hour: "2-digit", minute: "2-digit", hour12: true };
        el.innerText = "Updated " + new Intl.DateTimeFormat("en-US", options).format(latestTimestamp);
    }

    // --- Comfort Score Hero ---
    function renderComfortHero() {
        const ring = document.getElementById("scoreRing");
        const num = document.getElementById("comfortNumber");
        const label = document.getElementById("comfortLabel");
        const override = document.getElementById("comfortOverride");

        if (!currentComfort || currentComfort.length === 0) {
            num.textContent = "--";
            label.textContent = "No data";
            return;
        }

        const c = currentComfort[0];
        const score = Math.round(c.overall_score);
        num.textContent = score;
        label.textContent = "Swimming Comfort: " + c.label;
        ring.className = "comfort-score-ring " + c.label.toLowerCase();

        const explanation = document.getElementById("comfortExplanation");
        if (explanation) {
            explanation.textContent = getScoreExplanation(c);
        }

        if (c.override_reason) {
            override.textContent = c.override_reason;
        }

        renderConditions(c);
    }

    function renderConditions(c) {
        const strip = document.getElementById("conditionsStrip");
        if (!strip) return;

        const snapshot = c.input_snapshot || {};
        const pills = [];

        if (snapshot.water_temp_f != null) {
            pills.push({ label: "Water", value: snapshot.water_temp_f + "\u00B0F" });
        }
        if (snapshot.feels_like_f != null) {
            pills.push({ label: "Feels Like", value: Math.round(snapshot.feels_like_f) + "\u00B0F" });
        }
        if (snapshot.wind_mph != null) {
            pills.push({ label: "Wind", value: Math.round(snapshot.wind_mph) + " mph" });
        }
        if (snapshot.precip_pct != null) {
            pills.push({ label: "Rain", value: Math.round(snapshot.precip_pct) + "%" });
        }
        if (snapshot.uv_index != null) {
            pills.push({ label: "UV", value: Math.round(snapshot.uv_index) });
        }
        if (snapshot.aqi != null) {
            pills.push({ label: "AQI", value: Math.round(snapshot.aqi) });
        }
        if (snapshot.turbidity_ntu != null) {
            pills.push({ label: "Clarity", value: snapshot.turbidity_ntu + " NTU" });
        }

        strip.innerHTML = pills.map(p =>
            `<div class="condition-pill"><span class="pill-label">${p.label}</span>${p.value}</div>`
        ).join("");
    }

    // --- 7-Day Forecast Cards ---
    function renderForecast() {
        const container = document.getElementById("forecastCards");
        if (!container || !comfortForecast || comfortForecast.length === 0) {
            if (container) container.innerHTML = '<p style="color:#999;text-align:center;font-size:0.9rem;">No forecast data available yet.</p>';
            return;
        }

        const byDate = {};
        comfortForecast.forEach(row => {
            const dt = new Date(row.score_time);
            const dateKey = dt.toISOString().slice(0, 10);
            if (!byDate[dateKey]) {
                byDate[dateKey] = { rows: [], scores: [], labels: [], snapshots: [], hours: [] };
            }
            byDate[dateKey].rows.push(row);
            byDate[dateKey].scores.push(row.overall_score);
            byDate[dateKey].labels.push(row.label);
            byDate[dateKey].snapshots.push(row.input_snapshot || {});
            byDate[dateKey].hours.push(dt.getHours());
        });

        const days = Object.keys(byDate).sort().slice(0, 7);
        const dayNames = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"];
        const monthNames = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
                            "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];

        container.innerHTML = days.map(dateKey => {
            const group = byDate[dateKey];
            let bestIdx = -1;
            for (let i = 0; i < group.hours.length; i++) {
                if (group.hours[i] >= 11 && group.hours[i] <= 14) {
                    if (bestIdx === -1 || Math.abs(group.hours[i] - 12) < Math.abs(group.hours[bestIdx] - 12)) {
                        bestIdx = i;
                    }
                }
            }

            let score, labelText, bestRow;
            if (bestIdx >= 0) {
                score = Math.round(group.scores[bestIdx]);
                labelText = group.labels[bestIdx];
                bestRow = group.rows[bestIdx];
            } else {
                score = Math.round(group.scores.reduce((a, b) => a + b, 0) / group.scores.length);
                labelText = scoreLabel(score);
                bestRow = group.rows[0];
            }

            const rationale = getShortRationale(bestRow);

            const d = new Date(dateKey + "T12:00:00");
            const dayName = dayNames[d.getDay()];
            const dateStr = monthNames[d.getMonth()] + " " + d.getDate();
            const tierClass = labelText.toLowerCase();

            const temps = group.snapshots.map(s => s.feels_like_f).filter(t => t != null);
            let tempStr = "";
            if (temps.length > 0) {
                const hi = Math.round(Math.max(...temps));
                const lo = Math.round(Math.min(...temps));
                tempStr = `${hi}\u00B0 / ${lo}\u00B0`;
            }

            return `<div class="forecast-card">
                <div class="forecast-day">${dayName}<br>${dateStr}</div>
                <div class="forecast-score ${tierClass}">${score}</div>
                <div class="forecast-label-text">${labelText}</div>
                ${tempStr ? `<div class="forecast-temps">${tempStr}</div>` : ""}
                ${rationale ? `<div class="forecast-rationale">${rationale}</div>` : ""}
            </div>`;
        }).join("");
    }

    function scoreLabel(score) {
        if (score >= 80) return "Excellent";
        if (score >= 60) return "Good";
        if (score >= 40) return "Fair";
        if (score >= 20) return "Poor";
        return "Unsafe";
    }

    function getShortRationale(row) {
        // Build a brief 1-2 word reason from the weakest factor
        const factors = [];
        if (row.water_temp_score != null) factors.push({ score: row.water_temp_score, text: "Cold water" });
        if (row.air_temp_score != null) factors.push({ score: row.air_temp_score, text: "Cold air" });
        if (row.wind_score != null) factors.push({ score: row.wind_score, text: "Windy" });
        if (row.sun_score != null) factors.push({ score: row.sun_score, text: "Overcast" });
        if (row.rain_score != null) factors.push({ score: row.rain_score, text: "Rainy" });
        if (row.clarity_score != null && row.clarity_score < 60) factors.push({ score: row.clarity_score, text: "Murky" });
        if (row.algae_score != null && row.algae_score < 60) factors.push({ score: row.algae_score, text: "Algae" });
        if (row.aqi_score != null && row.aqi_score < 60) factors.push({ score: row.aqi_score, text: "Bad air" });

        const weak = factors.filter(f => f.score < 50).sort((a, b) => a.score - b.score);
        if (weak.length === 0) return "";
        return weak.slice(0, 2).map(f => f.text).join(", ");
    }

    // --- Year-over-year comparison ---
    function renderComparison() {
        const el = document.getElementById("comparisonText");
        if (!el) return;

        const now = new Date();
        const todayPacificStr = new Intl.DateTimeFormat("en-US", {
            timeZone: "America/Los_Angeles",
            year: "numeric", month: "2-digit", day: "2-digit"
        }).format(now);

        const [month, day, year] = todayPacificStr.split("/");
        const todayStr = `${year}-${month.padStart(2, "0")}-${day.padStart(2, "0")}`;
        const todayTempEntry = dataCurrent.find(entry => entry.date.startsWith(todayStr));
        const todayTemp = todayTempEntry ? todayTempEntry.max_temperature_f : null;
        const todayMonthDay = todayStr.slice(5);
        const pastTempsForToday = dataPast.filter(entry => entry.date.slice(5, 10) === todayMonthDay);
        const pastAvgTemp = pastTempsForToday.length
            ? (pastTempsForToday.reduce((sum, entry) => sum + Number(entry.max_temperature_f), 0) / pastTempsForToday.length).toFixed(1)
            : null;

        if (todayTemp !== null && pastAvgTemp !== null) {
            const tempDiff = (todayTemp - pastAvgTemp).toFixed(1);
            let text = `Water is ${todayTemp}\u00B0F today`;
            if (tempDiff > 0) text += ` \u2014 ${tempDiff}\u00B0F warmer than the ${pastTempsForToday.length}-year average`;
            else if (tempDiff < 0) text += ` \u2014 ${Math.abs(tempDiff)}\u00B0F colder than the ${pastTempsForToday.length}-year average`;
            else text += ` \u2014 right at the ${pastTempsForToday.length}-year average`;
            el.textContent = text;
        } else if (todayTemp !== null) {
            el.textContent = `Water is ${todayTemp}\u00B0F today`;
        }
    }

    // --- Expandable water temp chart ---
    let waterTempChartRendered = false;

    function setupToggles() {
        const toggle = document.getElementById("toggleWaterTemp");
        const chartEl = document.getElementById("waterTempChart");
        const arrow = document.getElementById("waterTempArrow");
        const valueEl = document.getElementById("waterTempValue");

        // Show current temp in the toggle bar
        if (valueEl && dataCurrent && dataCurrent.length > 0) {
            const latest = dataCurrent[dataCurrent.length - 1];
            valueEl.textContent = latest.max_temperature_f + "\u00B0F";
        }

        if (toggle && chartEl) {
            toggle.addEventListener("click", function () {
                const isHidden = chartEl.style.display === "none";
                chartEl.style.display = isHidden ? "block" : "none";
                arrow.classList.toggle("open", isHidden);

                if (isHidden && !waterTempChartRendered) {
                    renderWaterTempChart();
                    waterTempChartRendered = true;
                }
            });
        }
    }

    function renderWaterTempChart() {
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

        const years = Array.from(new Set(dataPast.map(row => row.pYear)));
        years.sort((a, b) => b - a);
        years.forEach((year, index) => {
            const filteredData = dataPast.filter(item => item.pYear === year);
            let grayValue = Math.round((index / Math.max(years.length - 1, 1)) * 200);
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
                borderDash: [6, 3],
                pointRadius: 3,
                fill: false,
                tension: 0.2
            });
        });

        const temperatureBands = [
            { min: 40, max: 50, color: "rgba(46, 134, 193, 0.6)", label: "Ice Cold (below 50)" },
            { min: 50, max: 60, color: "rgba(93, 173, 226, 0.6)", label: "Very Cold (50-60)" },
            { min: 60, max: 68, color: "rgba(174, 214, 241, 0.6)", label: "Cold (60-68)" },
            { min: 68, max: 75, color: "rgba(250, 215, 160, 0.6)", label: "Tolerable (68-75)" },
            { min: 75, max: 80, color: "rgba(245, 176, 65, 0.6)", label: "Pleasant (75-80)" },
            { min: 80, max: 90, color: "rgba(231, 76, 60, 0.6)", label: "Excellent (above 80)" }
        ];

        function getResponsiveFontSize(canvas) {
            const width = canvas.clientWidth;
            return Math.min(28, Math.max(22, width / 15));
        }

        const backgroundBandsPlugin = {
            id: "backgroundBands",
            beforeDraw: (chart) => {
                const { ctx, chartArea: { left, right }, scales: { y } } = chart;
                const canvas = chart.canvas;
                const fontSize = getResponsiveFontSize(canvas);
                ctx.save();
                temperatureBands.forEach(band => {
                    ctx.fillStyle = band.color;
                    ctx.fillRect(left, y.getPixelForValue(band.max), right - left, y.getPixelForValue(band.min) - y.getPixelForValue(band.max));
                    ctx.fillStyle = "black";
                    ctx.font = `${fontSize}px Arial`;
                    ctx.fillText(band.label, left + 10, y.getPixelForValue((band.min + band.max) / 2));
                });
                ctx.restore();
            }
        };

        const canvas = document.getElementById("lakeChart");
        const ctx = canvas.getContext("2d");
        const dpr = window.devicePixelRatio || 1;
        canvas.width = canvas.clientWidth * dpr;
        canvas.height = canvas.clientHeight * dpr;
        ctx.scale(dpr, dpr);

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
                        title: { display: false },
                        ticks: { display: false },
                        grid: { display: false },
                        min: new Date(new Date().setDate(new Date().getDate() - 7)),
                        max: new Date(new Date().setDate(new Date().getDate() + 7))
                    },
                    y: {
                        suggestedMin: 40,
                        suggestedMax: 90,
                        title: { display: false },
                        ticks: { display: false },
                        grid: { display: false }
                    }
                },
                plugins: {
                    legend: {
                        position: "top",
                        labels: {
                            usePointStyle: true,
                            font: { size: getResponsiveFontSize(canvas) * 0.8 },
                            boxWidth: 10,
                            boxHeight: 10,
                            padding: 20
                        }
                    },
                    tooltip: {
                        callbacks: {
                            label: function (tooltipItem) {
                                return `${tooltipItem.dataset.label}: ${tooltipItem.raw.y}\u00B0F`;
                            }
                        }
                    }
                }
            },
            plugins: [backgroundBandsPlugin]
        });
    }

    // Render all sections
    renderTimestamp();
    renderComfortHero();
    renderForecast();
    renderComparison();
    setupToggles();
});
