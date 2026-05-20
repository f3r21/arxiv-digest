(() => {
  const search = document.getElementById('cat-search');
  const list = document.getElementById('cat-list');
  const groups = list ? list.querySelectorAll('.cat-group') : [];
  const allOptions = list ? list.querySelectorAll('.cat-option') : [];
  const countEl = document.getElementById('selected-count');
  const clearBtn = document.getElementById('clear-cats');
  const form = document.getElementById('subscribe-form') || document.getElementById('manage-form');
  const status = document.getElementById('form-status');
  const submitBtn = document.getElementById('submit-btn');
  const presetsRoot = document.getElementById('presets');
  const presets = (window.__PRESETS__ || []).reduce((acc, p) => {
    acc[p.id] = new Set(p.codes);
    return acc;
  }, {});

  function getChecked() {
    if (!list) return new Set();
    return new Set(
      Array.from(list.querySelectorAll('input[name="categories"]:checked'))
        .map((cb) => cb.value),
    );
  }

  function updateCount() {
    if (!countEl) return;
    countEl.textContent = String(getChecked().size);
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
      let visible = 0;
      group.querySelectorAll('.cat-option').forEach((opt) => {
        const hay = opt.dataset.search || '';
        const ok = terms.every((t) => hay.includes(t));
        opt.classList.toggle('hidden', !ok);
        if (ok) visible += 1;
      });
      group.style.display = visible ? '' : 'none';
      if (visible) group.open = true;
    });
  }

  function syncPresetActiveStates() {
    if (!presetsRoot) return;
    const checked = getChecked();
    presetsRoot.querySelectorAll('.preset[data-preset-id]').forEach((btn) => {
      const id = btn.dataset.presetId;
      const codes = presets[id];
      if (!codes) return;
      const allOn = Array.from(codes).every((c) => checked.has(c));
      btn.classList.toggle('active', allOn);
    });
  }

  function togglePreset(id) {
    const codes = presets[id];
    if (!codes || !list) return;
    const checked = getChecked();
    const allOn = Array.from(codes).every((c) => checked.has(c));
    codes.forEach((code) => {
      const cb = list.querySelector(`input[name="categories"][value="${code}"]`);
      if (cb) cb.checked = !allOn;
    });
    // Abrir grupos donde caen las cats
    list.querySelectorAll('.cat-group').forEach((group) => {
      const matches = group.querySelectorAll(
        'input[name="categories"]:checked',
      ).length;
      if (matches > 0) group.open = true;
    });
    updateCount();
    syncPresetActiveStates();
  }

  if (search) search.addEventListener('input', applyFilter);

  if (list) {
    list.addEventListener('change', (e) => {
      if (e.target && e.target.name === 'categories') {
        updateCount();
        syncPresetActiveStates();
      }
    });
  }

  if (presetsRoot) {
    presetsRoot.addEventListener('click', (e) => {
      const btn = e.target.closest('.preset[data-preset-id]');
      if (btn) togglePreset(btn.dataset.presetId);
    });
  }

  if (clearBtn) {
    clearBtn.addEventListener('click', () => {
      list
        .querySelectorAll('input[name="categories"]:checked')
        .forEach((cb) => (cb.checked = false));
      updateCount();
      syncPresetActiveStates();
    });
  }

  if (form && form.id === 'subscribe-form') {
    form.addEventListener('submit', async (e) => {
      e.preventDefault();
      const checked = getChecked();
      if (checked.size === 0) {
        showStatus('Pick at least one category (or use a preset).', true);
        return;
      }
      submitBtn.disabled = true;
      submitBtn.textContent = 'Sending...';
      try {
        const data = new FormData(form);
        const resp = await fetch('/subscribe', { method: 'POST', body: data });
        if (resp.status === 202) {
          const body = await resp.json();
          showStatus(
            `✓ Confirmation email sent to ${body.email}. Click the link inside to activate.`,
            false,
          );
          form.reset();
          updateCount();
          syncPresetActiveStates();
        } else if (resp.status === 429) {
          showStatus(
            'Too many attempts from your IP. Please wait a moment.',
            true,
          );
        } else {
          let detail = 'Subscription failed.';
          try {
            const body = await resp.json();
            if (body && body.detail) detail = body.detail;
          } catch (_) {}
          showStatus(detail, true);
        }
      } catch (err) {
        showStatus('Network error. Try again.', true);
      } finally {
        submitBtn.disabled = false;
        submitBtn.textContent = 'Confirm by email →';
      }
    });
  }

  function showStatus(text, isError) {
    if (!status) return;
    status.textContent = text;
    status.classList.toggle('error', !!isError);
    status.classList.toggle('success', !isError);
    status.hidden = false;
    status.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
  }

  // Init
  updateCount();
  syncPresetActiveStates();
})();
