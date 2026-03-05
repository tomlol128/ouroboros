document.addEventListener('DOMContentLoaded', () => {
  const statusElement = document.getElementById('status');
  const identityElement = document.getElementById('identity-content');

  const updateDashboard = () => {
    fetch('/ouroboros/api/status.json')
      .then(response => response.json())
      .then(data => {
        statusElement.innerHTML = `
          <h2>Status</h2>
          <p>Version: ${data.version}</p>
          <p>Budget: $${data.budget_remaining.toFixed(2)} remaining</p>
          <p>Last activity: ${new Date(data.last_message_at).toLocaleString()}</p>
          <p>Status: <span class="${data.status}">${data.status}</span></p>
        `;
        
        identityElement.textContent = data.identity_snapshot;
      })
      .catch(error => {
        statusElement.innerHTML = `<h2>Status</h2><p class="error">Error loading status: ${error.message}</p>`;
      });
  };

  // Initial update
  updateDashboard();
  
  // Refresh every 30 seconds
  setInterval(updateDashboard, 30000);
});