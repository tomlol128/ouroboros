document.addEventListener('DOMContentLoaded', () => {
  const statusElement = document.getElementById('status');
  const identityElement = document.getElementById('identity-content');
  const thoughtsElement = document.getElementById('thoughts-content');
  const tasksElement = document.getElementById('tasks-content');

  const updateDashboard = () => {
    fetch('/ouroboros/api/status')
      .then(response => response.json())
      .then(data => {
        statusElement.innerHTML = `
          <h2>Status</h2>
          <p>Version: ${data.version}</p>
          <p>Budget: $${data.budget_remaining.toFixed(2)} remaining</p>
          <p>Active: ${data.active ? '✅' : '❌'}</p>
          <p>Last update: ${new Date(data.last_updated).toLocaleTimeString()}</p>
        `;
        
        identityElement.textContent = data.identity_snapshot;
        
        if (data.thought_process) {
          thoughtsElement.innerHTML = `<div class="thought-bubble">${data.thought_process}</div>`;
        }

        if (data.active_tasks && data.active_tasks.length > 0) {
          tasksElement.innerHTML = data.active_tasks.map(task => 
            `<div class="task-card">
              <div class="task-id">${task.id}</div>
              <div class="task-desc">${task.description}</div>
              <div class="task-meta">Type: ${task.type} | Runtime: ${task.runtime}</div>
            </div>`
          ).join('');
        } else {
          tasksElement.innerHTML = '<div class="empty">No active tasks</div>';
        }
      })
      .catch(error => {
        console.error('API error:', error);
        statusElement.innerHTML = `Error loading status: ${error.message}`;
        tasksElement.innerHTML = 'Unable to load tasks';
      });
  };

  // Initial update
  updateDashboard();
  
  // Refresh every 30 seconds
  setInterval(updateDashboard, 30000);
});