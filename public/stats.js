/**
 * SSS-Goldsprint Statistics & Highscores Controller
 */

const UI = {
    searchBox: document.getElementById('riderSearchInput'),
    searchSuggestions: document.getElementById('search-suggestions'),
    searchBtn: document.getElementById('searchBtn'),
    searchResults: document.getElementById('searchResults'),
    highscoreBody: document.getElementById('highscoreBody'),
    filterBtns: document.querySelectorAll('.filter-btn')
};

let currentCategory = 'All';
let currentTimeFilter = 'all';

async function fetchHighscores() {
    try {
        const response = await fetch(`/api/highscores?category=${currentCategory}&filter=${currentTimeFilter}`);
        const data = await response.json();
        renderHighscores(data);
    } catch (err) {
        console.error("Failed to fetch highscores:", err);
    }
}

function renderHighscores(data) {
    UI.highscoreBody.innerHTML = '';
    if (data.length === 0) {
        UI.highscoreBody.innerHTML = '<tr><td colspan="5" style="text-align:center; padding: 20px; color:#aaa;">No results found for this selection.</td></tr>';
        return;
    }

    data.forEach((row, index) => {
        const tr = document.createElement('tr');
        const dateStr = new Date(row.race_date).toLocaleDateString();
        tr.innerHTML = `
            <td>${index + 1}</td>
            <td style="color: #ff9800; font-weight: bold;">${row.name}</td>
            <td style="font-family: monospace; font-size: 1.2rem;">${row.race_time.toFixed(3)}s</td>
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
            <h3>${name}</h3>
            <p>Total Races: ${data.length}</p>
            <p>Personal Best: <strong>${data[0].race_time.toFixed(3)}s</strong> (${data[0].category})</p>
            <div class="rider-history">
                <h4>Recent Times</h4>
                ${data.slice(0, 5).map(r => `
                    <div class="history-row">
                        <span>${r.race_time.toFixed(3)}s</span>
                        <span style="font-size: 0.8rem; color:#888;">${r.category} - ${new Date(r.race_date).toLocaleDateString()}</span>
                    </div>
                `).join('')}
            </div>
        </div>
    `;
}

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

// Init
fetchHighscores();
