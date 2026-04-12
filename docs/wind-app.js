document.addEventListener("DOMContentLoaded", function () {

    // === Zone Definitions (wind prediction points, centered in open water) ===
    var ZONES = [
        { id: "north", name: "North End", lat: 47.640, lon: -122.092 },
        { id: "ne_shore", name: "NE Shore", lat: 47.622, lon: -122.078 },
        { id: "mid_west", name: "The Cove", lat: 47.612, lon: -122.102 },
        { id: "mid_east", name: "Mid-Lake East", lat: 47.600, lon: -122.082 },
        { id: "south_central", name: "South Central", lat: 47.580, lon: -122.090 },
        { id: "south_end", name: "South End", lat: 47.565, lon: -122.082 },
    ];

    // Points of interest (non-wind, shown as labels on the map)
    var POIS = [
        { name: "Boat Launch", lat: 47.558, lon: -122.062, icon: "\u2693" },
    ];

    // Hazard areas (shown as warning markers)
    var HAZARDS = [
        { name: "Sunken Forest", lat: 47.560, lon: -122.078, desc: "Submerged stumps" },
        { name: "Shallow Area", lat: 47.652, lon: -122.097, desc: "Bear Creek delta" },
    ];

    // Sheltering parameters per zone: fetch distance (km) and terrain shelter (0-1)
    // for 8 compass directions the wind blows FROM: N, NE, E, SE, S, SW, W, NW
    // fetch = how far wind travels over open water before reaching this spot
    // terrain = how much upwind hills/trees block the wind (0=none, 1=full)
    var SHELTER = {
        north:         { fetch: [0.2, 0.3, 0.8, 5.0, 10.0, 6.0, 1.0, 0.2], terrain: [0.1, 0.1, 0.4, 0.0, 0.0, 0.0, 0.6, 0.2] },
        ne_shore:      { fetch: [2.0, 0.2, 0.2, 0.3, 6.0,  8.0, 2.0, 1.0], terrain: [0.0, 0.5, 0.5, 0.5, 0.0, 0.0, 0.0, 0.0] },
        mid_west:      { fetch: [4.0, 2.0, 2.0, 1.0, 5.0,  0.2, 0.1, 0.3], terrain: [0.0, 0.0, 0.0, 0.3, 0.0, 0.8, 0.9, 0.7] },
        mid_east:      { fetch: [4.0, 0.3, 0.2, 0.3, 5.0,  5.0, 2.0, 2.0], terrain: [0.0, 0.4, 0.5, 0.4, 0.0, 0.0, 0.0, 0.0] },
        south_central: { fetch: [7.0, 3.0, 1.0, 0.5, 2.0,  0.5, 0.5, 4.0], terrain: [0.0, 0.0, 0.4, 0.5, 0.3, 0.5, 0.7, 0.1] },
        south_end:     { fetch: [10.0,5.0, 0.3, 0.2, 0.2,  0.3, 0.3, 3.0], terrain: [0.0, 0.0, 0.5, 0.6, 0.7, 0.6, 0.7, 0.1] },
    };

    var DIR_LABELS = ["N", "NE", "E", "SE", "S", "SW", "W", "NW"];

    // === SVG Map Constants ===
    var SVG_W = 300, SVG_H = 680;
    var LAT_MIN = 47.550, LAT_MAX = 47.660;
    var LON_MIN = -122.120, LON_MAX = -122.048;

    // Lake outline from OpenStreetMap (Douglas-Peucker simplified, 104 pts)
    var LAKE_OUTLINE = [
        [47.55622, -122.07318], [47.55679, -122.07370], [47.55648, -122.07459], [47.55529, -122.07441],
        [47.55600, -122.07746], [47.55866, -122.07956], [47.56299, -122.08021], [47.56810, -122.08270],
        [47.57008, -122.08565], [47.56981, -122.08964], [47.57157, -122.09239], [47.57052, -122.09490],
        [47.57164, -122.09675], [47.57327, -122.10671], [47.57543, -122.11010], [47.57714, -122.11163],
        [47.57866, -122.11116], [47.58014, -122.11183], [47.58198, -122.11066], [47.58608, -122.10987],
        [47.59175, -122.11060], [47.59667, -122.10958], [47.59874, -122.10825], [47.60122, -122.11023],
        [47.60572, -122.11181], [47.60849, -122.10917], [47.61157, -122.10761], [47.61351, -122.10340],
        [47.61835, -122.09677], [47.62087, -122.09130], [47.62550, -122.08763], [47.62983, -122.08687],
        [47.63224, -122.08741], [47.63478, -122.08914], [47.63584, -122.09195], [47.63754, -122.09292],
        [47.64158, -122.10119], [47.64257, -122.10172], [47.64342, -122.10123], [47.64548, -122.10466],
        [47.64852, -122.10656], [47.64942, -122.10642], [47.64990, -122.10702], [47.65053, -122.10662],
        [47.65254, -122.10804], [47.65303, -122.10764], [47.65247, -122.10432], [47.65491, -122.10034],
        [47.65575, -122.09770], [47.65546, -122.09504], [47.65495, -122.09484], [47.65573, -122.09447],
        [47.65526, -122.09323], [47.65208, -122.09059], [47.64981, -122.08967], [47.64258, -122.08235],
        [47.64202, -122.08263], [47.64254, -122.08378], [47.64183, -122.08367], [47.63960, -122.07873],
        [47.63581, -122.07398], [47.63277, -122.07150], [47.62708, -122.07083], [47.62394, -122.07186],
        [47.62164, -122.06972], [47.61825, -122.06842], [47.61666, -122.06836], [47.61572, -122.06930],
        [47.61290, -122.06918], [47.60342, -122.07922], [47.60234, -122.08145], [47.60116, -122.08188],
        [47.59947, -122.08088], [47.59710, -122.08236], [47.59535, -122.08528], [47.59257, -122.08666],
        [47.59103, -122.08844], [47.58874, -122.08644], [47.58752, -122.08684], [47.58611, -122.08481],
        [47.58409, -122.08442], [47.58250, -122.08319], [47.58007, -122.07692], [47.57606, -122.07468],
        [47.57376, -122.07082], [47.57188, -122.06864], [47.56996, -122.06760], [47.56907, -122.06636],
        [47.56770, -122.05749], [47.56660, -122.05575], [47.56518, -122.05575], [47.56506, -122.05519],
        [47.56350, -122.05559], [47.56204, -122.05740], [47.56344, -122.06069], [47.56227, -122.06430],
        [47.56232, -122.06651], [47.56125, -122.06463], [47.55959, -122.06504], [47.55821, -122.06636],
        [47.55733, -122.06925], [47.55787, -122.07072], [47.55661, -122.07156], [47.55622, -122.07318],
    ];

    function latLonToSvg(lat, lon) {
        var x = (lon - LON_MIN) / (LON_MAX - LON_MIN) * SVG_W;
        var y = (LAT_MAX - lat) / (LAT_MAX - LAT_MIN) * SVG_H;
        return [x, y];
    }

    // === Sheltering Model ===
    function dirBucket(deg) { return Math.round((deg || 0) / 45) % 8; }

    function computeChop(windMph, gustMph, dirDeg, zoneId) {
        var s = SHELTER[zoneId];
        if (!s) return { effectiveWind: windMph, chopScore: 50 };
        var bucket = dirBucket(dirDeg);
        var fetchKm = s.fetch[bucket];
        var shelter = s.terrain[bucket];

        // Effective wind reduced by terrain sheltering (up to 60% reduction)
        var effectiveWind = windMph * (1 - shelter * 0.6);

        // Chop builds over open-water fetch distance (saturates at ~3km)
        var fetchFactor = Math.min(1, fetchKm / 3.0);

        // Chop score: 100 = glass, 0 = too rough
        var score = 100;
        score -= effectiveWind * 7 * fetchFactor;       // base wind penalty
        score -= Math.max(0, gustMph - windMph) * 3 * fetchFactor; // gustiness penalty

        return {
            effectiveWind: Math.round(effectiveWind * 10) / 10,
            chopScore: Math.max(0, Math.min(100, Math.round(score)))
        };
    }

    function chopLabel(s) {
        if (s >= 80) return "Glass";
        if (s >= 60) return "Rideable";
        if (s >= 40) return "Choppy";
        return "Too Rough";
    }

    function chopColor(s) {
        if (s >= 80) return "#27ae60";
        if (s >= 60) return "#d4ac0d";
        if (s >= 40) return "#e67e22";
        return "#e74c3c";
    }

    // === Data Fetching ===
    function fetchWindData() {
        var lats = ZONES.map(function (z) { return z.lat; }).join(",");
        var lons = ZONES.map(function (z) { return z.lon; }).join(",");
        var url = "https://api.open-meteo.com/v1/forecast" +
            "?latitude=" + lats +
            "&longitude=" + lons +
            "&hourly=wind_speed_10m,wind_direction_10m,wind_gusts_10m" +
            "&wind_speed_unit=mph" +
            "&timezone=America/Los_Angeles" +
            "&forecast_hours=12";

        return fetch(url)
            .then(function (r) { return r.json(); })
            .then(processApiData)
            .catch(function () {
                // Fallback to static JSON generated by pipeline
                return fetch("wind-data.json?d=" + new Date().toISOString().slice(0, 10))
                    .then(function (r) { return r.json(); });
            });
    }

    function processApiData(raw) {
        if (!Array.isArray(raw)) raw = [raw];

        var now = new Date();
        var ch = new Date(now);
        ch.setMinutes(0, 0, 0);
        var pad = function (n) { return String(n).padStart(2, "0"); };
        var chStr = ch.getFullYear() + "-" + pad(ch.getMonth() + 1) + "-" +
            pad(ch.getDate()) + "T" + pad(ch.getHours()) + ":00";

        var zones = [];
        for (var i = 0; i < ZONES.length; i++) {
            var hourly = raw[i].hourly;
            var times = hourly.time;
            var idx = times.indexOf(chStr);
            if (idx === -1) idx = 0;

            var zh = [];
            for (var h = 0; h < Math.min(12, times.length - idx); h++) {
                var hi = idx + h;
                var wind = hourly.wind_speed_10m[hi] || 0;
                var gust = hourly.wind_gusts_10m[hi] || 0;
                var dir = hourly.wind_direction_10m[hi] || 0;
                var result = computeChop(wind, gust, dir, ZONES[i].id);
                zh.push({
                    time: times[hi],
                    wind_mph: Math.round(wind * 10) / 10,
                    wind_dir_deg: Math.round(dir),
                    gust_mph: Math.round(gust * 10) / 10,
                    effective_wind_mph: result.effectiveWind,
                    chop_score: result.chopScore,
                    chop_label: chopLabel(result.chopScore)
                });
            }

            var cur = zh[0] || {};
            zones.push({
                id: ZONES[i].id, name: ZONES[i].name,
                lat: ZONES[i].lat, lon: ZONES[i].lon,
                wind_mph: cur.wind_mph, wind_dir_deg: cur.wind_dir_deg,
                gust_mph: cur.gust_mph, effective_wind_mph: cur.effective_wind_mph,
                chop_score: cur.chop_score, chop_label: cur.chop_label,
                hourly: zh
            });
        }

        var best = zones.reduce(function (a, b) { return a.chop_score >= b.chop_score ? a : b; });
        return {
            generated_at: now.toISOString(),
            zones: zones,
            recommendation: {
                zone_id: best.id, zone_name: best.name,
                chop_score: best.chop_score, chop_label: best.chop_label
            }
        };
    }

    // === Rendering ===
    function render(data) {
        var zones = data.zones;
        var best = zones.reduce(function (a, b) { return (a.chop_score || 0) >= (b.chop_score || 0) ? a : b; });

        // Subtitle
        var subtitle = document.getElementById("subtitle");
        var allGlass = zones.every(function (z) { return z.chop_score >= 80; });
        var allRough = zones.every(function (z) { return z.chop_score < 40; });
        if (allGlass) subtitle.textContent = "Glass conditions across the lake";
        else if (allRough) subtitle.textContent = "Rough conditions — not ideal for surfing";
        else subtitle.textContent = best.chop_label + " at " + best.name;

        // Timestamp
        var ts = new Date(data.generated_at);
        var timeStr = new Intl.DateTimeFormat("en-US", { hour: "numeric", minute: "2-digit", hour12: true }).format(ts);
        document.getElementById("last-updated").textContent = "Updated " + timeStr;

        // Recommendation card
        var rec = document.getElementById("recommendation");
        document.getElementById("recBadge").textContent = best.chop_score;
        document.getElementById("recBadge").style.background = chopColor(best.chop_score);
        document.getElementById("recTitle").textContent = best.chop_label + " at " + best.name;
        var dirLabel = DIR_LABELS[dirBucket(best.wind_dir_deg)];
        var detail = dirLabel + " wind at " + best.wind_mph + " mph";
        if (best.gust_mph > best.wind_mph + 2) detail += " · Gusts " + best.gust_mph + " mph";
        detail += " · Effective " + best.effective_wind_mph + " mph";
        document.getElementById("recDetail").textContent = detail;
        rec.classList.add("visible");

        renderMap(zones, best.id);
    }

    // === SVG Helpers ===
    function svgEl(tag, attrs) {
        var el = document.createElementNS("http://www.w3.org/2000/svg", tag);
        for (var k in attrs) el.setAttribute(k, attrs[k]);
        return el;
    }

    // === Map Rendering ===
    function renderMap(zones, bestId) {
        var container = document.getElementById("mapContainer");
        var svg = svgEl("svg", { viewBox: "0 0 " + SVG_W + " " + SVG_H, class: "lake-map" });

        // Arrowhead marker definition
        var defs = svgEl("defs", {});
        var marker = svgEl("marker", {
            id: "arrowhead", markerWidth: "8", markerHeight: "6",
            refX: "8", refY: "3", orient: "auto"
        });
        marker.appendChild(svgEl("polygon", { points: "0 0, 8 3, 0 6", fill: "#555" }));
        defs.appendChild(marker);
        svg.appendChild(defs);

        // Land background
        svg.appendChild(svgEl("rect", { width: SVG_W, height: SVG_H, fill: "#e8e0d4", rx: "12" }));

        // Lake water
        var pts = LAKE_OUTLINE.map(function (p) {
            var xy = latLonToSvg(p[0], p[1]);
            return xy[0].toFixed(1) + "," + xy[1].toFixed(1);
        }).join(" ");
        svg.appendChild(svgEl("polygon", { points: pts, fill: "#c5dff0", stroke: "#8bb5d4", "stroke-width": "1.5" }));

        // Compass N indicator (arrow points up = north)
        var nx = SVG_W - 22;
        svg.appendChild(svgEl("line", {
            x1: nx, y1: 42, x2: nx, y2: 18,
            stroke: "#bbb", "stroke-width": "1.5",
            "marker-end": "url(#arrowhead)"
        }));
        var cText = svgEl("text", {
            x: nx, y: 14, "text-anchor": "middle",
            fill: "#999", "font-size": "11", "font-weight": "600"
        });
        cText.textContent = "N";
        svg.appendChild(cText);

        // Label offsets per zone (to avoid overlap with arrows/circles)
        var labelOffsets = {
            north:         { dx: 26, dy: -8 },
            ne_shore:      { dx: 26, dy: -8 },
            mid_west:      { dx: -26, dy: -8, anchor: "end" },
            mid_east:      { dx: 26, dy: -8 },
            south_central: { dx: 26, dy: -8 },
            south_end:     { dx: -26, dy: -8, anchor: "end" },
        };

        // Zone markers
        zones.forEach(function (zone) {
            var pos = latLonToSvg(zone.lat, zone.lon);
            var color = chopColor(zone.chop_score);
            var isBest = zone.id === bestId;

            // Highlight ring for best zone
            if (isBest) {
                svg.appendChild(svgEl("circle", {
                    cx: pos[0], cy: pos[1], r: "25",
                    fill: "none", stroke: color, "stroke-width": "3",
                    opacity: "0.5", class: "best-ring"
                }));
            }

            // Zone circle
            svg.appendChild(svgEl("circle", {
                cx: pos[0], cy: pos[1], r: "18",
                fill: color, stroke: "#fff", "stroke-width": "2.5"
            }));

            // Score number inside circle
            var scoreText = svgEl("text", {
                x: pos[0], y: pos[1] + 1, "text-anchor": "middle",
                "dominant-baseline": "central", fill: "#fff",
                "font-size": "13", "font-weight": "700"
            });
            scoreText.textContent = zone.chop_score;
            svg.appendChild(scoreText);

            // Wind arrow showing direction wind is blowing TO
            if (zone.wind_dir_deg != null && zone.wind_mph > 0) {
                var rad = zone.wind_dir_deg * Math.PI / 180;
                // Wind dir is where wind comes FROM; arrow shows where it blows TO
                var dx = -Math.sin(rad);
                var dy = Math.cos(rad);
                var startOff = 22;
                var arrowLen = Math.min(28, 14 + zone.wind_mph);
                svg.appendChild(svgEl("line", {
                    x1: pos[0] + dx * startOff, y1: pos[1] + dy * startOff,
                    x2: pos[0] + dx * (startOff + arrowLen),
                    y2: pos[1] + dy * (startOff + arrowLen),
                    stroke: "#555", "stroke-width": "2",
                    "marker-end": "url(#arrowhead)"
                }));
            }

            // Zone label
            var lo = labelOffsets[zone.id] || { dx: 26, dy: -8 };
            var label = svgEl("text", {
                x: pos[0] + lo.dx, y: pos[1] + lo.dy,
                "text-anchor": lo.anchor || "start",
                fill: "#666", "font-size": "10", "font-weight": "500"
            });
            label.textContent = zone.name;
            svg.appendChild(label);
        });

        // Hazard markers (warning triangles)
        HAZARDS.forEach(function (hz) {
            var hpos = latLonToSvg(hz.lat, hz.lon);
            var triSize = 8;
            var triPts = [
                (hpos[0]) + "," + (hpos[1] - triSize),
                (hpos[0] - triSize * 0.85) + "," + (hpos[1] + triSize * 0.6),
                (hpos[0] + triSize * 0.85) + "," + (hpos[1] + triSize * 0.6)
            ].join(" ");
            svg.appendChild(svgEl("polygon", {
                points: triPts, fill: "#d35400", stroke: "#fff", "stroke-width": "1.5"
            }));
            var hText = svgEl("text", {
                x: hpos[0], y: hpos[1] - 1, "text-anchor": "middle",
                "dominant-baseline": "central", fill: "#fff",
                "font-size": "9", "font-weight": "700"
            });
            hText.textContent = "!";
            svg.appendChild(hText);
            var hLabel = svgEl("text", {
                x: hpos[0], y: hpos[1] + triSize + 11,
                "text-anchor": "middle", fill: "#d35400",
                "font-size": "8", "font-weight": "600"
            });
            hLabel.textContent = hz.name;
            svg.appendChild(hLabel);
        });

        // Points of interest
        POIS.forEach(function (poi) {
            var ppos = latLonToSvg(poi.lat, poi.lon);
            var pIcon = svgEl("text", {
                x: ppos[0], y: ppos[1] + 2, "text-anchor": "middle",
                "dominant-baseline": "central",
                "font-size": "16"
            });
            pIcon.textContent = poi.icon;
            svg.appendChild(pIcon);
            var pLabel = svgEl("text", {
                x: ppos[0], y: ppos[1] + 16,
                "text-anchor": "middle", fill: "#555",
                "font-size": "9", "font-weight": "600"
            });
            pLabel.textContent = poi.name;
            svg.appendChild(pLabel);
        });

        // Geographic labels
        var geoLabels = [
            { text: "Redmond", lat: 47.658, lon: -122.085 },
            { text: "Issaquah", lat: 47.552, lon: -122.078 },
        ];
        geoLabels.forEach(function (gl) {
            var gpos = latLonToSvg(gl.lat, gl.lon);
            var gt = svgEl("text", {
                x: gpos[0], y: gpos[1], "text-anchor": "middle",
                fill: "#aaa", "font-size": "11", "font-style": "italic"
            });
            gt.textContent = gl.text;
            svg.appendChild(gt);
        });

        // Insert SVG before the overlays (keep header and rec card on top)
        var header = document.getElementById("mapHeader");
        var rec = document.getElementById("recommendation");
        container.insertBefore(svg, header);
    }

    // === Init ===
    fetchWindData().then(render).catch(function (err) {
        console.error("Failed to load wind data:", err);
        document.getElementById("subtitle").textContent = "Failed to load wind data";
    });
});
