(() => {
  const search = document.getElementById('cat-search');
  const list = document.getElementById('cat-list');
  const groups = list ? list.querySelectorAll('.cat-group') : [];
  const allOptions = list ? list.querySelectorAll('.cat-option') : [];
  const countEl = document.getElementById('selected-count');
  const clearBtn = document.getElementById('clear-cats');
  const form = document.getElementById('subscribe-form');
  const status = document.getElementById('form-status');
  const submitBtn = document.getElementById('submit-btn');

  function updateCount() {
    const n = list ? list.querySelectorAll('input[name="categories"]:checked').length : 0;
    if (countEl) countEl.textContent = String(n);
  }

  function applyFilter() {
    if (!search) return;
    const q = search.value.trim().toLowerCase();
    if (!q) {
      allOptions.forEach((o) => o.classList.remove('hidden'));
      groups.forEach((g) => (g.style.display = ''));
      return;
    }
    const terms = q.split(/\s+/).filter(Boolean);
    groups.forEach((group) => {
      let visibleInGroup = 0;
      group.querySelectorAll('.cat-option').forEach((opt) => {
        const hay = opt.dataset.search || '';
        const match = terms.every((t) => hay.includes(t));
        opt.classList.toggle('hidden', !match);
        if (match) visibleInGroup += 1;
      });
      group.style.display = visibleInGroup ? '' : 'none';
      if (visibleInGroup) group.open = true;
    });
  }

  if (search) search.addEventListener('input', applyFilter);

  if (list) {
    list.addEventListener('change', (e) => {
      if (e.target && e.target.name === 'categories') updateCount();
    });
  }

  if (clearBtn) {
    clearBtn.addEventListener('click', () => {
      list
        .querySelectorAll('input[name="categories"]:checked')
        .forEach((cb) => (cb.checked = false));
      updateCount();
    });
  }

  if (form) {
    form.addEventListener('submit', async (e) => {
      e.preventDefault();
      const checked = form.querySelectorAll('input[name="categories"]:checked');
      if (checked.length === 0) {
        showStatus('Elige al menos una categoria.', true);
        return;
      }
      submitBtn.disabled = true;
      submitBtn.textContent = 'Enviando...';
      try {
        const data = new FormData(form);
        const resp = await fetch('/subscribe', { method: 'POST', body: data });
        if (resp.status === 202) {
          showStatus(
            'Listo. Revisa tu correo y haz click en el link de confirmacion.',
            false,
          );
          form.reset();
          updateCount();
        } else if (resp.status === 429) {
          showStatus(
            'Demasiados intentos desde tu IP. Espera un rato y vuelve a intentar.',
            true,
          );
        } else {
          let detail = 'Error al suscribirte.';
          try {
            const body = await resp.json();
            if (body && body.detail) detail = body.detail;
          } catch (_) {}
          showStatus(detail, true);
        }
      } catch (err) {
        showStatus('Error de red. Intentalo de nuevo.', true);
      } finally {
        submitBtn.disabled = false;
        submitBtn.textContent = 'Suscribirme';
      }
    });
  }

  function showStatus(text, isError) {
    if (!status) return;
    status.textContent = text;
    status.classList.toggle('error', !!isError);
    status.hidden = false;
  }

  updateCount();
})();
