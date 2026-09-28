/* Same-origin Python integration. A failed Python request is surfaced, never silently replaced. */
(() => {
  async function request(path, options = {}) {
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), 10000);
    try {
      const response = await fetch(path, { ...options, signal: controller.signal });
      if (!response.ok) throw new Error(`Demo API returned ${response.status}`);
      return await response.json();
    } finally {
      clearTimeout(timeout);
    }
  }
  window.programApi = {
    async search(question) {
      if (window.DEMO_API_ENABLED) {
        return request('/api/search', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ question })
        });
      }
      return {
        ...window.demoSearch(question, window.programCatalog.getPrograms()),
        demo: window.programCatalog.isDemo()
      };
    }
  };
  if (window.DEMO_API_ENABLED) {
    request('/api/programs').then(data => {
      window.programCatalog.setPrograms(data.programs, { demo: data.demo });
    }).catch(() => {
      const note = document.getElementById('connection-note') || document.getElementById('catalog-note');
      if (note) note.textContent = 'Python catalog unavailable. Showing bundled demo programs. Restart the Python server and reload.';
    });
  }
})();
