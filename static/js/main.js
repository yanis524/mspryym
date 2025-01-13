// Seahawks Monitoring main JavaScript file

// Fonction pour mettre à jour les badges de statut
function updateStatusBadges() {
    document.querySelectorAll('[data-status]').forEach(badge => {
        const status = badge.dataset.status;
        badge.className = `badge ${status === 'connected' ? 'bg-success' : 'bg-danger'}`;
        badge.textContent = status === 'connected' ? 'Connectée' : 'Déconnectée';
    });
}

// Fonction pour formater les dates
function formatDate(dateString) {
    if (!dateString) return 'Jamais';
    const date = new Date(dateString);
    return date.toLocaleString('fr-FR');
}

// Fonction pour mettre à jour les statistiques du dashboard
function updateDashboardStats(harvesterId) {
    if (!harvesterId) return;

    fetch(`/api/dashboard-data/${harvesterId}`)
        .then(response => response.json())
        .then(data => {
            // Mise à jour des statistiques
            document.querySelectorAll('[data-stat]').forEach(element => {
                const stat = element.dataset.stat;
                if (data.stats && data.stats[stat] !== undefined) {
                    element.textContent = data.stats[stat];
                }
            });

            // Mise à jour du statut de la sonde
            const statusBadge = document.querySelector('#harvester-status');
            if (statusBadge) {
                statusBadge.className = `badge ${data.harvester.status === 'connected' ? 'bg-success' : 'bg-danger'}`;
                statusBadge.textContent = data.harvester.status === 'connected' ? 'Connectée' : 'Déconnectée';
            }

            // Mise à jour de la dernière activité
            const lastSeen = document.querySelector('#last-seen');
            if (lastSeen && data.harvester.last_seen) {
                lastSeen.textContent = formatDate(data.harvester.last_seen);
            }
        })
        .catch(error => console.error('Erreur lors de la mise à jour:', error));
}

// Fonction pour mettre à jour le tableau des dernières analyses
function updateRecentScans(data) {
    // Update recent scans table
    const tbody = document.querySelector('#recent-scans tbody');
    tbody.innerHTML = '';
    
    data.recent_scans.forEach(scan => {
        const tr = document.createElement('tr');
        tr.innerHTML = `
            <td>${formatDate(scan.timestamp)}</td>
            <td>${scan.harvester_name}</td>
            <td>${scan.device_count}</td>
            <td><span class="badge bg-success">Completed</span></td>
        `;
        tbody.appendChild(tr);
    });
}

// Initialisation des tooltips Bootstrap
document.addEventListener('DOMContentLoaded', function() {
    // Initialiser les tooltips Bootstrap
    var tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });

    // Mettre à jour les statuts toutes les 30 secondes
    const harvesterId = document.querySelector('[data-harvester-id]')?.dataset.harvesterId;
    if (harvesterId) {
        updateDashboardStats(harvesterId);
        setInterval(() => updateDashboardStats(harvesterId), 30000);
    }

    // Auto-refresh dashboard data every 30 seconds
    if (window.location.pathname === '/') {
        fetch('/api/dashboard-data')
            .then(response => response.json())
            .then(data => {
                // Update statistics
                document.getElementById('harvester-count').textContent = data.harvester_count;
                document.getElementById('device-count').textContent = data.device_count;
                document.getElementById('scan-count').textContent = data.scan_count;

                updateRecentScans(data);
            })
            .catch(error => console.error('Error:', error));

        setInterval(function() {
            fetch('/api/dashboard-data')
                .then(response => response.json())
                .then(data => {
                    // Update statistics
                    document.getElementById('harvester-count').textContent = data.harvester_count;
                    document.getElementById('device-count').textContent = data.device_count;
                    document.getElementById('scan-count').textContent = data.scan_count;

                    updateRecentScans(data);
                })
                .catch(error => console.error('Error:', error));
        }, 30000);
    }
});
