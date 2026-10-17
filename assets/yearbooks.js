import { validateBook } from './catalogue-policy.js';

(() => {
  const grid = document.querySelector('#yearbook-grid');
  if (!grid) return;

  const search = document.querySelector('#yearbook-search');
  const filters = document.querySelector('#decade-filters');
  const count = document.querySelector('#result-count');
  const colours = ['#213387', '#4457a6', '#42517f', '#303f79', '#5869ad', '#1d2c70'];
  let books = [];
  let activeDecade = 'all';

  const escapeHtml = (value) => String(value).replace(/[&<>'"]/g, (char) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', "'": '&#39;', '"': '&quot;' })[char]);

  function renderFilters() {
    const decades = ['all', ...new Set(books.map((book) => String(Math.floor(book.year / 10) * 10)))];
    filters.innerHTML = decades.map((decade) => `<button type="button" class="filter-pill${decade === activeDecade ? ' active' : ''}" data-decade="${decade}">${decade === 'all' ? 'All' : `${decade}s`}</button>`).join('');
  }

  function render() {
    const term = search.value.trim().toLowerCase();
    const shown = books.filter((book) => {
      const inDecade = activeDecade === 'all' || Math.floor(book.year / 10) * 10 === Number(activeDecade);
      return inDecade && `${book.year} ${book.title} ${book.edition || ''}`.toLowerCase().includes(term);
    });
    count.textContent = `${shown.length} ${shown.length === 1 ? 'edition' : 'editions'}`;
    if (!shown.length) {
      grid.innerHTML = '<div class="empty-state"><h2>No yearbooks match that search.</h2><p>Try a four-digit year or choose a different decade.</p></div>';
      return;
    }
    grid.innerHTML = shown.map((book, index) => {
      const state = book.state || 'missing';
      const label = state === 'local' ? 'On this mirror' : state === 'remote' ? 'Google Drive copy' : state === 'wayback' ? 'Wayback copy' : state === 'preserved' ? 'Preserved copy' : 'Awaiting file';
      const action = book.url
        ? `<a href="${escapeHtml(book.url)}" ${state !== 'local' ? 'rel="external"' : ''}>Open yearbook <span aria-hidden="true">↗</span></a>`
        : '<button type="button" disabled>Link not available</button>';
      return `<article class="yearbook-card" data-state="${state}" style="--card-color:${colours[index % colours.length]}">
        <div class="card-top"><span>${escapeHtml(book.school || 'PCSS')}</span><span class="yearbook-status"><i></i>${label}</span></div>
        <h2>${book.year}</h2><p>${escapeHtml(book.edition || book.title || 'Yearbook')}</p>${action}</article>`;
    }).join('');
  }

  filters.addEventListener('click', (event) => {
    const button = event.target.closest('[data-decade]');
    if (!button) return;
    activeDecade = button.dataset.decade;
    renderFilters();
    render();
  });
  search.addEventListener('input', render);

  fetch('data/yearbooks.json')
    .then((response) => {
      if (!response.ok) throw new Error(`Catalogue request failed: ${response.status}`);
      return response.json();
    })
    .then((data) => {
      if (!Array.isArray(data.books)) throw new Error('Invalid catalogue');
      books = data.books.map(validateBook);
      const requested = new URLSearchParams(location.search).get('decade');
      if (requested && books.some((book) => Math.floor(book.year / 10) * 10 === Number(requested))) activeDecade = requested;
      renderFilters();
      render();
    })
    .catch(() => {
      count.textContent = 'Catalogue unavailable';
      grid.innerHTML = '<div class="empty-state"><h2>The catalogue could not be loaded.</h2><p>Try serving the site over HTTP instead of opening this file directly.</p></div>';
    });
})();

