document.addEventListener("DOMContentLoaded", function () {

    let activeChart = null;
    let activePillKey = null;

    // Approximate sunset hour for Lake Sammamish by month (Pacific time)
    function getSunsetHour(month) {
        //                  Jan  Feb  Mar  Apr  May  Jun  Jul  Aug  Sep  Oct  Nov  Dec
        const sunsetHours = [17,  17.5, 18.5, 19.5, 20, 21, 21, 20.5, 19.5, 18.5, 17, 16.5];
        return sunsetHours[month];
    }

    // Plugin: shades nighttime bands + marks "Today" on time-series charts
    function daylightPlugin() {
        return {
            id: "daylight",
            beforeDraw: (chart) => {
                const { ctx, chartArea: { left, right, top, bottom }, scales: { x } } = chart;
                if (!x || !x.min || !x.max) return;
                const DAWN = 7; // 7 AM

                ctx.save();
                ctx.fillStyle = "rgba(0,0,0,0.07)";

                // Walk each day in the chart range
                const startDay = new Date(x.min); startDay.setHours(0, 0, 0, 0);
                const endMs = x.max;
                for (let d = new Date(startDay); d.getTime() <= endMs; d.setDate(d.getDate() + 1)) {
                    const sunset = getSunsetHour(d.getMonth());

                    // Pre-dawn band: midnight to DAWN
                    const nightStart = new Date(d); nightStart.setHours(0, 0, 0, 0);
                    const dawnTime = new Date(d); dawnTime.setHours(DAWN, 0, 0, 0);
                    const x1 = Math.max(x.getPixelForValue(nightStart.getTime()), left);
                    const x2 = Math.min(x.getPixelForValue(dawnTime.getTime()), right);
                    if (x2 > x1) ctx.fillRect(x1, top, x2 - x1, bottom - top);

                    // Post-sunset band: sunset to midnight
                    const sunsetTime = new Date(d); sunsetTime.setHours(Math.floor(sunset), (sunset % 1) * 60, 0, 0);
                    const midnight = new Date(d); midnight.setDate(midnight.getDate() + 1); midnight.setHours(0, 0, 0, 0);
                    const x3 = Math.max(x.getPixelForValue(sunsetTime.getTime()), left);
                    const x4 = Math.min(x.getPixelForValue(midnight.getTime()), right);
                    if (x4 > x3) ctx.fillRect(x3, top, x4 - x3, bottom - top);
                }

                ctx.restore();
            }
        };
    }

    // Plugin: draws a vertical crosshair line at the hovered x position
    function crosshairPlugin() {
        return {
            id: "crosshair",
            afterDraw: (chart) => {
                if (!chart.tooltip || !chart.tooltip.caretX) return;
                const { ctx, chartArea: { top, bottom } } = chart;
                const x = chart.tooltip.caretX;
                ctx.save();
                ctx.setLineDash([3, 3]);
                ctx.strokeStyle = "rgba(0,0,0,0.15)";
                ctx.lineWidth = 1;
                ctx.beginPath();
                ctx.moveTo(x, top);
                ctx.lineTo(x, bottom);
                ctx.stroke();
                ctx.setLineDash([]);
                ctx.restore();
            }
        };
    }

    // Format a Date for tooltip title: "Today 3 PM", "Mon 10 AM", etc.
    function tooltipTitle(items) {
        if (!items.length) return "";
        const dt = new Date(items[0].raw.x);
        const now = new Date();
        const isToday = dt.getFullYear() === now.getFullYear() &&
                        dt.getMonth() === now.getMonth() &&
                        dt.getDate() === now.getDate();
        const dayLabel = isToday ? "Today" : ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"][dt.getDay()];
        const hour = dt.getHours();
        const ampm = hour >= 12 ? "PM" : "AM";
        const h = hour % 12 || 12;
        return `${dayLabel} ${h} ${ampm}`;
    }

    // X-axis tick callback: "Today", "Mon", "Tue", etc.
    function dayOfWeekTick(value, index, ticks) {
        const dt = new Date(value);
        const now = new Date();
        const isToday = dt.getFullYear() === now.getFullYear() &&
                        dt.getMonth() === now.getMonth() &&
                        dt.getDate() === now.getDate();
        if (isToday) return "Today";
        return ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"][dt.getDay()];
    }

    // Plugin: draws a horizontal dotted threshold line with a label
    function thresholdPlugin(value, label, color) {
        return {
            id: "threshold_" + value,
            afterDraw: (chart) => {
                const { ctx, chartArea: { left, right }, scales: { y } } = chart;
                const yPos = y.getPixelForValue(value);
                if (yPos < chart.chartArea.top || yPos > chart.chartArea.bottom) return;
                ctx.save();
                ctx.setLineDash([6, 4]);
                ctx.strokeStyle = color || "rgba(0,0,0,0.25)";
                ctx.lineWidth = 1.5;
                ctx.beginPath();
                ctx.moveTo(left, yPos);
                ctx.lineTo(right, yPos);
                ctx.stroke();
                ctx.setLineDash([]);
                ctx.fillStyle = color ? color.replace(/[\d.]+\)$/, "0.85)") : "rgba(0,0,0,0.6)";
                ctx.font = "12px sans-serif";
                ctx.fillText(label, right - ctx.measureText(label).width - 6, yPos - 5);
                ctx.restore();
            }
        };
    }

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
        return "Mainly due to " + weak.slice(0, 3).map(f => f.text).join(", ");
    }

    // --- Timestamp ---
    function formatRelativeTime(ts) {
        const now = new Date();
        const isToday = ts.getFullYear() === now.getFullYear() &&
                        ts.getMonth() === now.getMonth() &&
                        ts.getDate() === now.getDate();
        const timeStr = new Intl.DateTimeFormat("en-US", { hour: "numeric", minute: "2-digit", hour12: true }).format(ts);
        if (isToday) return "today, " + timeStr;
        const yesterday = new Date(now); yesterday.setDate(now.getDate() - 1);
        const isYesterday = ts.getFullYear() === yesterday.getFullYear() &&
                            ts.getMonth() === yesterday.getMonth() &&
                            ts.getDate() === yesterday.getDate();
        if (isYesterday) return "yesterday, " + timeStr;
        const dateStr = new Intl.DateTimeFormat("en-US", { month: "short", day: "numeric" }).format(ts);
        return dateStr + ", " + timeStr;
    }

    function renderTimestamp() {
        const el = document.getElementById("last-updated");
        if (!el) return;
        const meta = (typeof dataMeta !== "undefined" && dataMeta && dataMeta.length) ? dataMeta[0] : null;
        if (meta && meta.generated_at) {
            el.innerText = "Updated " + formatRelativeTime(new Date(meta.generated_at));
            return;
        }
        // Fallback to buoy data
        if (dataCurrent && dataCurrent.length > 0) {
            const ts = new Date(dataCurrent[dataCurrent.length - 1].date);
            el.innerText = "Updated " + formatRelativeTime(ts);
        }
    }

    // --- Staleness helpers ---
    function getBuoyStaleness() {
        const meta = (typeof dataMeta !== "undefined" && dataMeta && dataMeta.length) ? dataMeta[0] : null;
        if (!meta || !meta.latest_buoy) return null;
        const buoyTime = new Date(meta.latest_buoy);
        const now = new Date();
        const hoursAgo = (now - buoyTime) / (1000 * 60 * 60);
        if (hoursAgo < 12) return null; // fresh enough
        return { hoursAgo: Math.round(hoursAgo), time: buoyTime };
    }

    function getStalenessText(key) {
        // Only buoy-dependent pills show staleness
        const buoyKeys = ["water", "clarity"];
        if (!buoyKeys.includes(key)) return "";
        const stale = getBuoyStaleness();
        if (!stale) return "";
        const ago = stale.hoursAgo;
        if (ago < 48) return `Buoy data is ${ago} hours old (updated ${formatRelativeTime(stale.time)})`;
        const days = Math.round(ago / 24);
        return `Buoy data is ${days} days old (updated ${formatRelativeTime(stale.time)})`;
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
        num.textContent = Math.round(c.overall_score);
        label.textContent = c.label;
        ring.className = "comfort-score-ring " + c.label.toLowerCase();

        const explanation = document.getElementById("comfortExplanation");
        if (explanation) explanation.textContent = getScoreExplanation(c);

        if (c.override_reason) override.textContent = c.override_reason;

        // Make the score ring clickable to show breakdown
        ring.style.cursor = "pointer";
        ring.addEventListener("click", function () {
            if (activePillKey === "breakdown") {
                closeDetailPanel();
            } else {
                openDetailPanel("breakdown");
            }
        });

        renderConditions(c);
    }

    // --- Conditions pills (toggle buttons) ---
    function renderConditions(c) {
        const strip = document.getElementById("conditionsStrip");
        if (!strip) return;

        const snapshot = c.input_snapshot || {};
        const pills = [];

        if (snapshot.water_temp_f != null)
            pills.push({ key: "water", label: "Water", value: snapshot.water_temp_f + "\u00B0F", score: c.water_temp_score });
        if (snapshot.feels_like_f != null)
            pills.push({ key: "feels_like", label: "Feels Like", value: Math.round(snapshot.feels_like_f) + "\u00B0F", score: c.air_temp_score });
        if (snapshot.wind_mph != null)
            pills.push({ key: "wind", label: "Wind", value: Math.round(snapshot.wind_mph) + " mph", score: c.wind_score });
        if (snapshot.precip_pct != null)
            pills.push({ key: "rain", label: "Rain", value: Math.round(snapshot.precip_pct) + "%", score: c.rain_score });
        if (snapshot.uv_index != null)
            pills.push({ key: "uv", label: "UV", value: Math.round(snapshot.uv_index), score: c.sun_score });
        if (snapshot.aqi != null)
            pills.push({ key: "aqi", label: "AQI", value: Math.round(snapshot.aqi), score: c.aqi_score });
        if (snapshot.turbidity_ntu != null)
            pills.push({ key: "clarity", label: "Clarity", value: snapshot.turbidity_ntu + " NTU", score: c.clarity_score });

        strip.innerHTML = pills.map(p => {
            let border = "";
            if (p.score != null) {
                if (p.score >= 70) border = "border-color:#27ae60";
                else if (p.score >= 40) border = "border-color:#e6a817";
                else border = "border-color:#e74c3c";
            }
            return `<button class="condition-pill" data-key="${p.key}" style="${border}"><span class="pill-label">${p.label}</span>${p.value}</button>`;
        }).join("");

        // Wire up click handlers
        strip.querySelectorAll(".condition-pill").forEach(btn => {
            btn.addEventListener("click", function () {
                const key = this.dataset.key;
                if (activePillKey === key) {
                    // Toggle off
                    closeDetailPanel();
                } else {
                    openDetailPanel(key);
                }
            });
        });
    }

    function openDetailPanel(key) {
        const panel = document.getElementById("detailPanel");
        const subtitle = document.getElementById("detailSubtitle");

        // Update active pill styling
        document.querySelectorAll(".condition-pill").forEach(el => el.classList.remove("active"));
        document.getElementById("scoreRing").classList.remove("ring-active");
        if (key === "breakdown") {
            document.getElementById("scoreRing").classList.add("ring-active");
        } else {
            const btn = document.querySelector(`.condition-pill[data-key="${key}"]`);
            if (btn) btn.classList.add("active");
        }

        activePillKey = key;
        panel.classList.add("visible");

        // Show staleness warning if applicable
        const stalenessEl = document.getElementById("detailStaleness");
        if (stalenessEl) stalenessEl.textContent = getStalenessText(key);

        // Destroy previous chart and ensure chart area is visible
        if (activeChart) { activeChart.destroy(); activeChart = null; }
        const wrap = document.getElementById("detailChartWrap");
        if (wrap) wrap.style.display = "";

        // Render the appropriate chart
        if (key === "breakdown") {
            subtitle.textContent = "Score breakdown";
            renderBreakdownChart();
        } else if (key === "water") {
            subtitle.textContent = getWaterSubtitle();
            renderWaterTempChart();
        } else if (key === "clarity") {
            const c = currentComfort && currentComfort[0];
            const snap = c ? (c.input_snapshot || {}) : {};
            const ntu = snap.turbidity_ntu;
            if (ntu != null) {
                subtitle.textContent = `Current turbidity: ${ntu} NTU` + (ntu < 2 ? " (clear)" : ntu < 5 ? " (slightly murky)" : " (murky)");
            } else {
                subtitle.textContent = "No turbidity data available";
            }
            // No chart for clarity — it's a single buoy reading, not a forecast
            const wrap = document.getElementById("detailChartWrap");
            if (wrap) wrap.style.display = "none";
            return;
        } else {
            subtitle.textContent = getChartTitle(key);
            renderForecastChart(key);
        }
    }

    function closeDetailPanel() {
        const panel = document.getElementById("detailPanel");
        panel.classList.remove("visible");
        document.querySelectorAll(".condition-pill").forEach(el => el.classList.remove("active"));
        document.getElementById("scoreRing").classList.remove("ring-active");
        activePillKey = null;
        if (activeChart) { activeChart.destroy(); activeChart = null; }
    }

    // --- Score breakdown bar chart ---
    function renderBreakdownChart() {
        const c = currentComfort && currentComfort[0];
        if (!c) return;

        const components = [
            { label: "Water Temp (30%)",  score: c.water_temp_score, weight: 0.30, color: "#2980b9" },
            { label: "Air Temp (20%)",    score: c.air_temp_score,   weight: 0.20, color: "#e67e22" },
            { label: "Wind (15%)",        score: c.wind_score,       weight: 0.15, color: "#3498db" },
            { label: "Sun (10%)",         score: c.sun_score,        weight: 0.10, color: "#f1c40f" },
            { label: "Rain (10%)",        score: c.rain_score,       weight: 0.10, color: "#7f8c8d" },
            { label: "Clarity (5%)",      score: c.clarity_score,    weight: 0.05, color: "#1abc9c" },
            { label: "Algae (2.5%)",      score: c.algae_score,      weight: 0.025, color: "#27ae60" },
            { label: "Air Quality (2.5%)",score: c.aqi_score,        weight: 0.025, color: "#9b59b6" },
        ].filter(d => d.score != null);

        const labels = components.map(d => d.label);
        const scores = components.map(d => Math.round(d.score));
        const weighted = components.map(d => Math.round(d.score * d.weight));
        const colors = components.map(d => d.color);

        const canvas = document.getElementById("detailChart");
        activeChart = new Chart(canvas, {
            type: "bar",
            data: {
                labels: labels,
                datasets: [{
                    label: "Score (0-100)",
                    data: scores,
                    backgroundColor: colors.map(c => c + "cc"),
                    borderColor: colors,
                    borderWidth: 1.5,
                    borderRadius: 4,
                }]
            },
            options: {
                indexAxis: "y",
                responsive: true, maintainAspectRatio: false,
                scales: {
                    x: {
                        min: 0, max: 100,
                        ticks: { font: { size: 12 } },
                        grid: { color: "rgba(0,0,0,0.05)" },
                        title: { display: true, text: "Component score", font: { size: 12 } }
                    },
                    y: {
                        ticks: { font: { size: 13 } },
                        grid: { display: false }
                    }
                },
                plugins: {
                    legend: { display: false },
                    tooltip: {
                        callbacks: {
                            afterLabel: (ti) => {
                                const d = components[ti.dataIndex];
                                return `Weighted contribution: ${(d.score * d.weight).toFixed(1)} of ${Math.round(d.weight * 100)} pts`;
                            }
                        }
                    }
                }
            },
            plugins: [{
                id: "vline50",
                afterDraw: (chart) => {
                    const { ctx, chartArea: { top, bottom }, scales: { x } } = chart;
                    const xPos = x.getPixelForValue(50);
                    ctx.save();
                    ctx.setLineDash([6, 4]);
                    ctx.strokeStyle = "rgba(0,0,0,0.2)";
                    ctx.lineWidth = 1.5;
                    ctx.beginPath();
                    ctx.moveTo(xPos, top);
                    ctx.lineTo(xPos, bottom);
                    ctx.stroke();
                    ctx.setLineDash([]);
                    ctx.restore();
                }
            }]
        });
    }

    function getChartTitle(key) {
        return key === "clarity" ? "" : "8-day forecast";
    }

    // --- Water temp subtitle with year-over-year comparison ---
    function getWaterSubtitle() {
        // Compare current water temp to historical average for this date
        const c = currentComfort && currentComfort[0];
        const currentTemp = c ? (c.input_snapshot || {}).water_temp_f : null;

        const now = new Date();
        const todayPacificStr = new Intl.DateTimeFormat("en-US", {
            timeZone: "America/Los_Angeles",
            year: "numeric", month: "2-digit", day: "2-digit"
        }).format(now);
        const [month, day, year] = todayPacificStr.split("/");
        const todayMD = `${month}-${day}`;
        const pastTemps = dataPast.filter(e => e.date.slice(5, 10) === todayMD);
        const pastAvg = pastTemps.length
            ? (pastTemps.reduce((s, e) => s + Number(e.max_temperature_f), 0) / pastTemps.length).toFixed(1)
            : null;

        if (currentTemp != null && pastAvg != null) {
            const diff = (currentTemp - pastAvg).toFixed(1);
            if (diff > 0) return `${diff}\u00B0F warmer than the ${pastTemps.length}-year average`;
            if (diff < 0) return `${Math.abs(diff)}\u00B0F colder than the ${pastTemps.length}-year average`;
            return `Right at the ${pastTemps.length}-year average`;
        }
        return "Projected water temperature";
    }

    // --- Water temperature forecast chart ---
    function renderWaterTempChart() {
        if (!comfortForecast || comfortForecast.length === 0) return;
        const data = comfortForecast
            .map(r => {
                const snap = r.input_snapshot || {};
                return snap.water_temp_f != null ? { x: new Date(r.score_time), y: snap.water_temp_f } : null;
            })
            .filter(Boolean);
        if (data.length === 0) return;
        const canvas = document.getElementById("detailChart");
        activeChart = new Chart(canvas, {
            type: "line",
            data: {
                datasets: [{
                    label: "Water Temperature",
                    data: data,
                    borderColor: "#2980b9",
                    backgroundColor: "#2980b922",
                    fill: true, borderWidth: 2.5, pointRadius: 0, tension: 0.3
                }]
            },
            options: {
                responsive: true, maintainAspectRatio: false,
                interaction: { mode: "index", intersect: false },
                scales: {
                    x: {
                        type: "time",
                        time: { unit: "day" },
                        ticks: { font: { size: 12 }, callback: dayOfWeekTick },
                        grid: { color: "rgba(0,0,0,0.05)" }
                    },
                    y: {
                        min: 40, max: 90,
                        ticks: { font: { size: 12 }, callback: v => v + "\u00B0F" },
                        grid: { color: "rgba(0,0,0,0.05)" }
                    }
                },
                plugins: {
                    legend: { display: false },
                    tooltip: {
                        callbacks: {
                            title: tooltipTitle,
                            label: ti => `${ti.raw.y}\u00B0F`
                        }
                    }
                }
            },
            plugins: [daylightPlugin(), crosshairPlugin(), thresholdPlugin(60, "Swimmable 60\u00B0F", "rgba(39,174,96,0.4)")]
        });
    }

    // --- Forecast line chart for a given metric ---
    function renderForecastChart(key) {
        if (!comfortForecast || comfortForecast.length === 0) return;

        const fieldMap = {
            feels_like: { field: "feels_like_f", unit: "\u00B0F", color: "#e67e22", min: 20, max: 120,
                threshold: { value: 65, label: "Comfortable 65\u00B0F", color: "rgba(39,174,96,0.4)" } },
            wind: { field: "wind_mph", unit: " mph", color: "#3498db", min: 0, max: 40,
                threshold: { value: 12, label: "Uncomfortable 12+ mph", color: "rgba(231,76,60,0.4)" } },
            rain: { field: "precip_pct", unit: "%", color: "#7f8c8d", min: 0, max: 100,
                threshold: { value: 50, label: "Likely rain 50%", color: "rgba(231,76,60,0.4)" } },
            uv: { field: "uv_index", unit: "", color: "#f39c12", min: 0, max: 12,
                threshold: { value: 6, label: "High UV 6+", color: "rgba(231,76,60,0.4)" } },
            aqi: { field: "aqi", unit: "", color: "#9b59b6", min: 0, max: 200,
                threshold: { value: 100, label: "Unhealthy 100+", color: "rgba(231,76,60,0.4)" } },
        };

        const cfg = fieldMap[key];
        if (!cfg) return;

        const data = comfortForecast
            .map(r => {
                const snap = r.input_snapshot || {};
                const val = snap[cfg.field];
                return val != null ? { x: new Date(r.score_time), y: Number(val) } : null;
            })
            .filter(Boolean);

        if (data.length === 0) return;

        const canvas = document.getElementById("detailChart");
        activeChart = new Chart(canvas, {
            type: "line",
            data: {
                datasets: [{
                    label: getChartTitle(key).split(" \u2014")[0],
                    data: data,
                    borderColor: cfg.color,
                    backgroundColor: cfg.color + "22",
                    fill: true, borderWidth: 2.5, pointRadius: 0, tension: 0.3
                }]
            },
            options: {
                responsive: true, maintainAspectRatio: false,
                interaction: { mode: "index", intersect: false },
                scales: {
                    x: {
                        type: "time",
                        time: { unit: "day" },
                        ticks: { font: { size: 12 }, callback: dayOfWeekTick },
                        grid: { color: "rgba(0,0,0,0.05)" }
                    },
                    y: {
                        min: cfg.min, max: cfg.max,
                        ticks: { font: { size: 12 } },
                        grid: { color: "rgba(0,0,0,0.05)" }
                    }
                },
                plugins: {
                    legend: { display: false },
                    tooltip: {
                        callbacks: {
                            title: tooltipTitle,
                            label: ti => `${ti.raw.y}${cfg.unit}`
                        }
                    }
                }
            },
            plugins: [daylightPlugin(), crosshairPlugin()].concat(cfg.threshold ? [thresholdPlugin(cfg.threshold.value, cfg.threshold.label, cfg.threshold.color)] : [])
        });
    }

    // --- 7-Day Forecast Cards ---
    function renderForecast() {
        const container = document.getElementById("forecastCards");
        if (!container || !comfortForecast || comfortForecast.length === 0) {
            if (container) container.innerHTML = '<p style="color:#999;text-align:center;font-size:0.9rem;">No forecast data yet.</p>';
            return;
        }

        const byDate = {};
        comfortForecast.forEach(row => {
            const dt = new Date(row.score_time);
            const dateKey = dt.toISOString().slice(0, 10);
            if (!byDate[dateKey]) byDate[dateKey] = { rows: [], scores: [], labels: [], snapshots: [], hours: [] };
            byDate[dateKey].rows.push(row);
            byDate[dateKey].scores.push(row.overall_score);
            byDate[dateKey].labels.push(row.label);
            byDate[dateKey].snapshots.push(row.input_snapshot || {});
            byDate[dateKey].hours.push(dt.getHours());
        });

        const days = Object.keys(byDate).sort().slice(0, 8);
        const dayNames = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"];
        const monthNames = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];

        container.innerHTML = days.map(dateKey => {
            const g = byDate[dateKey];
            let bestIdx = -1;
            for (let i = 0; i < g.hours.length; i++) {
                if (g.hours[i] >= 11 && g.hours[i] <= 14) {
                    if (bestIdx === -1 || Math.abs(g.hours[i] - 12) < Math.abs(g.hours[bestIdx] - 12))
                        bestIdx = i;
                }
            }

            let score, labelText, bestRow;
            if (bestIdx >= 0) {
                score = Math.round(g.scores[bestIdx]); labelText = g.labels[bestIdx]; bestRow = g.rows[bestIdx];
            } else {
                score = Math.round(g.scores.reduce((a, b) => a + b, 0) / g.scores.length);
                labelText = scoreLabel(score); bestRow = g.rows[0];
            }

            const rationale = getShortRationale(bestRow);
            const d = new Date(dateKey + "T12:00:00");
            const dayName = dayNames[d.getDay()];
            const dateStr = monthNames[d.getMonth()] + " " + d.getDate();
            const tier = labelText.toLowerCase();

            const temps = g.snapshots.map(s => s.feels_like_f).filter(t => t != null);
            let tempStr = "";
            if (temps.length > 0) {
                tempStr = `${Math.round(Math.max(...temps))}\u00B0/${Math.round(Math.min(...temps))}\u00B0`;
            }

            return `<div class="forecast-card">
                <div class="forecast-day">${dayName}<br>${dateStr}</div>
                <div class="forecast-score ${tier}">${score}</div>
                <div class="forecast-label-text">${labelText}</div>
                ${tempStr ? `<div class="forecast-temps">${tempStr}</div>` : ""}
                ${rationale ? `<div class="forecast-rationale">${rationale}</div>` : ""}
            </div>`;
        }).join("");
    }

    function scoreLabel(s) {
        if (s >= 80) return "Excellent";
        if (s >= 60) return "Good";
        if (s >= 40) return "Fair";
        if (s >= 20) return "Poor";
        return "Unsafe";
    }

    function getShortRationale(row) {
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

    // Render all sections
    renderTimestamp();
    renderComfortHero();
    renderForecast();
});
