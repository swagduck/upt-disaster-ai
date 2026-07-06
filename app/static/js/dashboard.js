// --- Global Variables & Chart Instances ---
let trendChartInstance = null;
let distChartInstance = null;
let magChartInstance = null;

// Premium Cyber-Military Theme Colors
const colors = {
    primary: '#0ea5e9',    // Light blue
    secondary: '#94a3b8',  // Slate gray
    accent: '#ef4444',     // Red
    bgLight: 'rgba(14, 165, 233, 0.1)',
    gridLines: '#1e293b',  // Dark slate
    hazards: {
        QUAKE: '#38bdf8',  // Sky blue
        FIRE: '#f97316',   // Orange
        VOLCANO: '#fbbf24',// Amber
        STORM: '#8b5cf6',  // Purple
        OTHER: '#64748b'   // Slate
    }
};

// Common Chart.js options for Cyberpunk look
Chart.defaults.color = colors.secondary;
Chart.defaults.font.family = "'Inter', 'Share Tech Mono', monospace";
Chart.defaults.plugins.tooltip.backgroundColor = '#0f172a';
Chart.defaults.plugins.tooltip.borderColor = '#1e293b';
Chart.defaults.plugins.tooltip.borderWidth = 1;

// --- Initialize Charts ---
function initCharts() {
    // 1. Trend Chart (Total Events over time)
    const ctxTrend = document.getElementById('trendChart').getContext('2d');
    trendChartInstance = new Chart(ctxTrend, {
        type: 'line',
        data: { labels: [], datasets: [{
            label: 'Total Active Hazards',
            data: [],
            borderColor: colors.primary,
            backgroundColor: colors.bgLight,
            borderWidth: 2,
            pointBackgroundColor: colors.bgLight,
            pointBorderColor: colors.primary,
            pointRadius: 2,
            pointHoverRadius: 5,
            fill: true,
            tension: 0.3
        }]},
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                x: { grid: { color: colors.gridLines } },
                y: { grid: { color: colors.gridLines }, beginAtZero: true }
            },
            plugins: { legend: { display: false } }
        }
    });

    // 2. Hazard Distribution (Doughnut)
    const ctxDist = document.getElementById('distChart').getContext('2d');
    distChartInstance = new Chart(ctxDist, {
        type: 'doughnut',
        data: { labels: [], datasets: [{
            data: [],
            backgroundColor: [colors.hazards.QUAKE, colors.hazards.FIRE, colors.hazards.VOLCANO, colors.hazards.STORM, colors.hazards.OTHER],
            borderColor: '#0b0f19', // Match app background
            borderWidth: 2,
            hoverOffset: 10
        }]},
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { position: 'right', labels: { color: colors.secondary, font: { size: 11 } } }
            },
            cutout: '75%'
        }
    });

    // 3. Max Magnitude Chart (Bar)
    const ctxMag = document.getElementById('magChart').getContext('2d');
    magChartInstance = new Chart(ctxMag, {
        type: 'bar',
        data: { labels: [], datasets: [{
            label: 'Max Magnitude (Scale)',
            data: [],
            backgroundColor: colors.accent,
            borderColor: colors.accent,
            borderWidth: 1,
            borderRadius: 4
        }]},
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                x: { grid: { display: false } },
                y: { grid: { color: colors.gridLines }, beginAtZero: true, max: 10.0 }
            },
            plugins: { legend: { display: false } }
        }
    });
}

// --- Fetch Data & Update UI ---
async function fetchSummary() {
    try {
        const res = await fetch('/api/v1/stats/summary');
        const data = await res.json();

        // Update Cards
        document.getElementById('val-total-snapshots').innerText = data.total_snapshots.toLocaleString();
        document.getElementById('val-total-events').innerText = data.total_events_recorded.toLocaleString();
        document.getElementById('val-max-mag').innerText = data.max_magnitude_ever.toFixed(1);
        document.getElementById('val-24h').innerText = data.snapshots_last_24h.toLocaleString();

        // Update Distribution Chart
        if (data.type_counts) {
            const labels = Object.keys(data.type_counts);
            const values = Object.values(data.type_counts);
            distChartInstance.data.labels = labels;
            distChartInstance.data.datasets[0].data = values;
            distChartInstance.update();
        }
    } catch (err) {
        console.error("Failed to fetch summary:", err);
    }
}

async function fetchTrend() {
    try {
        const res = await fetch('/api/v1/stats/trend?hours=24');
        const data = await res.json();
        
        if (data.points && data.points.length > 0) {
            // Format labels
            const labels = data.points.map(p => {
                const d = new Date(p.time);
                return `${d.getHours().toString().padStart(2,'0')}:${d.getMinutes().toString().padStart(2,'0')}`;
            });
            
            const totalEvents = data.points.map(p => p.total);
            const maxMags = data.points.map(p => p.max_mag);

            // Update Trend Chart
            trendChartInstance.data.labels = labels;
            trendChartInstance.data.datasets[0].data = totalEvents;
            trendChartInstance.update();

            // Update Mag Chart
            magChartInstance.data.labels = labels;
            magChartInstance.data.datasets[0].data = maxMags;
            magChartInstance.update();
        }
    } catch (err) {
        console.error("Failed to fetch trend:", err);
    }
}

// --- Lifecycle ---
window.onload = () => {
    initCharts();
    fetchSummary();
    fetchTrend();

    // Auto-refresh every 60 seconds
    setInterval(() => {
        fetchSummary();
        fetchTrend();
    }, 60000);
};
