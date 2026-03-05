class OuroborosDashboard {
    constructor() {
        this.init();
    }

    init() {
        this.startStatusPolling();
        this.loadIdentity();
        this.setupEventListeners();
    }

    async fetchStatus() {
        try {
            const response = await fetch('/ouroboros/api/status');
            if (!response.ok) throw new Error('Network response was not ok');
            const data = await response.json();
            this.updateStatus(data);
            return data;
        } catch (error) {
            this.showError('Failed to fetch status: ' + error.message);
            return null;
        }
    }

    async loadIdentity() {
        try {
            const response = await fetch('/ouroboros/api/identity');
            if (!response.ok) throw new Error('Network response was not ok');
            const data = await response.json();
            this.updateIdentity(data);
        } catch (error) {
            document.getElementById('identity-content').textContent = 
                'Failed to load identity: ' + error.message;
        }
    }

    updateStatus(data) {
        const statusElement = document.querySelector('#status p');
        if (data) {
            const statusHtml = `
                <div class="status-grid">
                    <div><strong>Version:</strong></div>
                    <div>${data.version || 'Unknown'}</div>
                    <div><strong>Branch:</strong></div>
                    <div>${data.branch || 'Unknown'}</div>
                    <div><strong>Budget:</strong></div>
                    <div>$${data.budget_remaining || 0} left</div>
                    <div><strong>Last Update:</strong></div>
                    <div>${new Date().toLocaleTimeString()}</div>
                </div>
            `;
            statusElement.innerHTML = statusHtml;
        }
    }

    updateIdentity(data) {
        const identityElement = document.getElementById('identity-content');
        identityElement.textContent = data.identity || 'No identity data available';
    }

    showError(message) {
        const statusElement = document.querySelector('#status p');
        statusElement.innerHTML = `<span class="error">❌ ${message}</span>`;
    }

    setupEventListeners() {
        // Auto-refresh every 30 seconds
        setInterval(() => {
            this.fetchStatus();
        }, 30000);

        // Manual refresh button
        const refreshBtn = document.createElement('button');
        refreshBtn.textContent = '🔄 Refresh';
        refreshBtn.className = 'refresh-btn';
        refreshBtn.onclick = () => this.fetchStatus();
        
        const statusCard = document.getElementById('status');
        statusCard.appendChild(refreshBtn);
    }
}

// Initialize dashboard when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    new OuroborosDashboard();
});

// Add CSS for status grid and button
const style = document.createElement('style');
style.textContent = `
    .status-grid {
        display: grid;
        grid-template-columns: 100px 200px;
        gap: 15px;
        margin-top: 15px;
    }
    .error {
        color: #e53e3e;
        font-weight: bold;
    }
    .refresh-btn {
        background: #667eea;
        color: white;
        border: none;
        padding: 8px 16px;
        border-radius: 6px;
        cursor: pointer;
        margin-top: 15px;
        font-size: 14px;
        transition: background 0.3s ease;
    }
    .refresh-btn:hover {
        background: #5a67d8;
    }
`;
document.head.appendChild(style);