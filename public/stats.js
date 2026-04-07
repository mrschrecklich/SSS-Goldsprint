/**
 * SSS-Goldsprint Statistics & Highscores Controller
 */

const UI = {
    searchBox: document.getElementById('riderSearchInput'),
    searchSuggestions: document.getElementById('search-suggestions'),
    searchBtn: document.getElementById('searchBtn'),
    searchResults: document.getElementById('searchResults'),
    highscoreBody: document.getElementById('highscoreBody'),
    filterBtns: document.querySelectorAll('.filter-btn'),
    distanceSort: document.getElementById('distanceSort')
};

let currentCategory = 'All';
let currentTimeFilter = 'all';

async function fetchHighscores() {
    try {
        const dist = UI.distanceSort.value;
        const response = await fetch(`/api/highscores?category=${currentCategory}&filter=${currentTimeFilter}${dist ? '&distance=' + dist : ''}`);
        const data = await response.json();
        renderHighscores(data);
    } catch (err) {
        console.error("Failed to fetch highscores:", err);
    }
}

function renderHighscores(data) {
    UI.highscoreBody.innerHTML = '';
    if (data.length === 0) {
        UI.highscoreBody.innerHTML = '<tr><td colspan="7" style="text-align:center; padding: 20px; color:#aaa;">No results found for this selection.</td></tr>';
        return;
    }

    data.forEach((row, index) => {
        const tr = document.createElement('tr');
        const dateStr = new Date(row.race_date).toLocaleDateString();
        tr.innerHTML = `
            <td>${index + 1}</td>
            <td style="color: #ff9800; font-weight: bold;">${row.name}</td>
            <td style="font-family: monospace; font-size: 1.2rem;">${row.race_time.toFixed(3)}s</td>
            <td>${row.race_distance}m</td>
            <td style="color: #2196F3;">${row.avg_speed_kmh.toFixed(1)} km/h</td>
            <td style="font-size: 0.9rem;">${row.category}</td>
            <td style="font-size: 0.8rem; color: #888;">${dateStr}</td>
        `;
        UI.highscoreBody.appendChild(tr);
    });
}

async function searchRider() {
    const name = UI.searchBox.value.trim();
    if (!name) return;

    try {
        const response = await fetch(`/api/participant/${encodeURIComponent(name)}`);
        if (response.status === 404) {
            UI.searchResults.innerHTML = `<div class="rider-card" style="text-align:center;">Rider "${name}" not found.</div>`;
            return;
        }
        const data = await response.json();
        renderRiderStats(name, data);
    } catch (err) {
        console.error("Search failed:", err);
    }
}

function renderRiderStats(name, data) {
    UI.searchResults.innerHTML = `
        <div class="rider-card">
            <div style="display:flex; justify-content:space-between; align-items:flex-start;">
                <div>
                    <h3>${name}</h3>
                    <p>Total Races: ${data.length}</p>
                    <p>Personal Best: <strong>${data[0].race_time.toFixed(3)}s</strong> (${data[0].category})</p>
                </div>
                <button onclick="deleteRider('${name}')" class="delete-btn">DELETE RIDER</button>
            </div>
            <div class="rider-history">
                <h4>Recent Times</h4>
                ${data.slice(0, 5).map(r => `
                    <div class="history-row">
                        <span>${r.race_time.toFixed(3)}s for ${r.race_distance}m</span>
                        <span style="font-size: 0.8rem; color:#888;">${r.category} - ${new Date(r.race_date).toLocaleDateString()}</span>
                    </div>
                `).join('')}
            </div>
        </div>
    `;
}

async function deleteRider(name) {
    if (!confirm(`Permanently delete all records for ${name}? This cannot be undone.`)) return;
    
    try {
        await fetch(`/api/participant/${encodeURIComponent(name)}`, { method: 'DELETE' });
        UI.searchResults.innerHTML = '';
        UI.searchBox.value = '';
        fetchHighscores();
    } catch (err) {
        alert("Failed to delete rider.");
    }
}
window.deleteRider = deleteRider;

// Event Listeners
UI.searchBox.addEventListener('input', async (e) => {
    const query = e.target.value;
    if (query.length < 2) {
        UI.searchSuggestions.innerHTML = '';
        return;
    }

    try {
        const response = await fetch(`/api/suggestions?q=${encodeURIComponent(query)}`);
        const names = await response.json();
        UI.searchSuggestions.innerHTML = names.map(n => `<option value="${n}">`).join('');
    } catch (err) {}
});

UI.searchBtn.addEventListener('click', searchRider);
UI.searchBox.addEventListener('keypress', (e) => {
    if (e.key === 'Enter') searchRider();
});

UI.filterBtns.forEach(btn => {
    btn.addEventListener('click', () => {
        const type = btn.dataset.type;
        const val = btn.dataset.value;

        // Toggle active class within group
        document.querySelectorAll(`.filter-btn[data-type="${type}"]`).forEach(b => b.classList.remove('active'));
        btn.classList.add('active');

        if (type === 'category') currentCategory = val;
        else if (type === 'time') currentTimeFilter = val;

        fetchHighscores();
    });
});

UI.distanceSort.addEventListener('change', fetchHighscores);

// Init
fetchHighscores();
