// === Utility helpers ===
const API = {
  lic:  (p='') => `/admin/api/licenses${p}`,
  ak:   (p='') => `/admin/api/apikeys${p}`,
  v:    (p='') => `/admin/api/voices${p}`,
  cfg:  () => `/admin/api/config`,
  logs: () => `/admin/api/logs`,
  upv:  () => `/admin/api/voices/upload`,
  bkp:  () => `/admin/api/backup`,
  bkpLic: () => `/admin/api/backup/licenses`,
  console: () => `/api`
};

const J = (sel) => document.querySelector(sel);
const JAll = (sel) => Array.from(document.querySelectorAll(sel));

async function jget(url) {
  const r = await fetch(url, { credentials: 'include' });
  if (r.status === 401) throw new Error('401 Unauthorized');
  return r.json();
}
async function jpost(url, body) {
  const r = await fetch(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    credentials: 'include',
    body: JSON.stringify(body || {})
  });
  if (r.status === 401) throw new Error('401 Unauthorized');
  return r.json();
}
async function jput(url, body) {
  const r = await fetch(url, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    credentials: 'include',
    body: JSON.stringify(body || {})
  });
  if (r.status === 401) throw new Error('401 Unauthorized');
  return r.json();
}
async function jdel(url) {
  const r = await fetch(url, { method: 'DELETE', credentials: 'include' });
  if (r.status === 401) throw new Error('401 Unauthorized');
  return r.json();
}

// === LICENSES ===
async function loadLicenses() {
  const q = new URLSearchParams();
  const s = J('#licSearch')?.value?.trim();
  const minc = J('#licMinCredit')?.value;
  const maxc = J('#licMaxCredit')?.value;
  const act = J('#licActiveFilter')?.value;
  const df = J('#licDateFrom')?.value;
  const dt = J('#licDateTo')?.value;
  if (s) q.set('q', s);
  if (minc) q.set('min_credit', minc);
  if (maxc) q.set('max_credit', maxc);
  if (act) q.set('active', act);
  if (df) q.set('date_from', df);
  if (dt) q.set('date_to', dt);

  const rows = await jget(API.lic(q.toString() ? `?${q.toString()}` : ''));
  const tb = J('#licTbody'); tb.innerHTML = '';
  for (const x of rows) {
    const tr = document.createElement('tr');
    tr.innerHTML = `
      <td>${x.id}</td>
      <td class="copyable" title="copy">${x.key}</td>
      <td>${x.mac_id ?? ''}</td>
      <td>${x.credit}</td>
      <td>${x.active ? '✅' : '⛔'}</td>
      <td>${x.created_at ?? ''}</td>
      <td>${x.updated_at ?? ''}</td>
      <td class="d-flex gap-1">
        <button class="btn btn-sm btn-outline-primary">Edit</button>
        <button class="btn btn-sm btn-outline-danger">Del</button>
        <button class="btn btn-sm btn-outline-success">Toggle</button>
      </td>`;
    tr.querySelector('.btn-outline-primary').onclick = () => fillLicForm(x);
    tr.querySelector('.btn-outline-danger').onclick = async () => { await jdel(API.lic(`/${x.id}`)); loadLicenses(); };
    tr.querySelector('.btn-outline-success').onclick = async () => { await jpost(API.lic(`/${x.id}/toggle`), {}); loadLicenses(); };
    tr.querySelector('.copyable').onclick = () => navigator.clipboard.writeText(x.key);
    tb.appendChild(tr);
  }
}
function resetLicenseForm() {
  J('#licId').value = '';
  J('#licFormTitle').innerText = 'Додати ліцензію';
  J('#licKey').value = '';
  J('#licMac').value = '';
  J('#licCredit').value = 0;
  J('#licActive').checked = true;
}
function fillLicForm(x) {
  J('#licId').value = x.id;
  J('#licFormTitle').innerText = `Редагувати #${x.id}`;
  J('#licKey').value = x.key;
  J('#licMac').value = x.mac_id || '';
  J('#licCredit').value = x.credit || 0;
  J('#licActive').checked = !!x.active;
}
async function submitLicense() {
  const id = J('#licId').value;
  const payload = {
    key: J('#licKey').value.trim(),
    mac_id: J('#licMac').value.trim() || null,
    credit: parseInt(J('#licCredit').value || '0', 10),
    active: J('#licActive').checked
  };
  if (id) await jput(API.lic(`/${id}`), payload);
  else    await jpost(API.lic(), payload);
  resetLicenseForm(); loadLicenses();
}
async function applyDelta() {
  const id = J('#licId').value;
  if (!id) return alert('Спочатку вибери ліцензію (Edit).');
  const delta = parseInt(J('#licDelta').value || '0', 10);
  await jpost(API.lic(`/${id}/credit`), { delta });
  J('#licDelta').value = '';
  loadLicenses();
}

// === API KEYS ===
async function loadApiKeys() {
  const rows = await jget(API.ak());
  const tb = J('#akTbody'); tb.innerHTML = '';
  for (const x of rows) {
    const tr = document.createElement('tr');
    tr.innerHTML = `
      <td>${x.id}</td>
      <td class="copyable" title="copy">${x.api_key}</td>
      <td>${x.status}</td>
      <td>${x.created_at ?? ''}</td>
      <td class="d-flex gap-1">
        <button class="btn btn-sm btn-outline-primary">Edit</button>
        <button class="btn btn-sm btn-outline-danger">Del</button>
      </td>`;
    tr.querySelector('.btn-outline-primary').onclick = () => {
      J('#akId').value = x.id; J('#akFormTitle').innerText = `Редагувати #${x.id}`;
      J('#akKey').value = x.api_key; J('#akStatus').value = x.status;
    };
    tr.querySelector('.btn-outline-danger').onclick = async () => { await jdel(API.ak(`/${x.id}`)); loadApiKeys(); };
    tr.querySelector('.copyable').onclick = () => navigator.clipboard.writeText(x.api_key);
    tb.appendChild(tr);
  }
}
function resetApiKeyForm() {
  J('#akId').value = ''; J('#akFormTitle').innerText = 'Додати API Key';
  J('#akKey').value = ''; J('#akStatus').value = 'active';
}
async function submitApiKey() {
  const id = J('#akId').value;
  const body = { api_key: J('#akKey').value.trim(), status: J('#akStatus').value };
  if (id) await jput(API.ak(`/${id}`), body);
  else    await jpost(API.ak(), body);
  resetApiKeyForm(); loadApiKeys();
}

// === VOICES ===
async function loadVoices() {
  const rows = await jget(API.v());
  const tb = J('#voicesTbody'); tb.innerHTML = '';
  for (const x of rows) {
    const tr = document.createElement('tr');
    tr.innerHTML = `
      <td>${x.id}</td><td>${x.name}</td><td class="copyable">${x.voice_id}</td>
      <td>${x.active ? '✅' : '⛔'}</td>
      <td class="d-flex gap-1">
        <button class="btn btn-sm btn-outline-primary">Edit</button>
        <button class="btn btn-sm btn-outline-danger">Del</button>
      </td>`;
    tr.querySelector('.btn-outline-primary').onclick = () => {
      J('#voiceId').value = x.id; J('#voiceFormTitle').innerText = `Редагувати #${x.id}`;
      J('#voiceName').value = x.name; J('#voiceVid').value = x.voice_id; J('#voiceActive').checked = !!x.active;
    };
    tr.querySelector('.btn-outline-danger').onclick = async () => { await jdel(API.v(`/${x.id}`)); loadVoices(); };
    tr.querySelector('.copyable').onclick = () => navigator.clipboard.writeText(x.voice_id);
    tb.appendChild(tr);
  }
}
function resetVoiceForm() {
  J('#voiceId').value=''; J('#voiceFormTitle').innerText='Додати голос';
  J('#voiceName').value=''; J('#voiceVid').value=''; J('#voiceActive').checked=true;
}
async function submitVoice() {
  const id = J('#voiceId').value;
  const body = { name: J('#voiceName').value.trim(), voice_id: J('#voiceVid').value.trim(), active: J('#voiceActive').checked };
  if (id) await jput(API.v(`/${id}`), body);
  else    await jpost(API.v(), body);
  resetVoiceForm(); loadVoices();
}
async function uploadVoices() {
  const f = J('#voiceFile').files?.[0];
  if (!f) return alert('Оберіть .txt файл');
  const fd = new FormData(); fd.append('file', f);
  const r = await fetch(API.upv(), { method:'POST', body: fd, credentials:'include' });
  if (r.status === 401) return alert('401 Unauthorized');
  const j = await r.json(); alert(`Додано: ${j.added || 0}`);
  loadVoices();
}

// === LOGS ===
async function loadLogs() {
  const q = new URLSearchParams();
  const s = J('#logSearch')?.value?.trim();
  const minc = J('#logMinChars')?.value;
  const maxc = J('#logMaxChars')?.value;
  const act = J('#logAction')?.value;
  const df = J('#logDateFrom')?.value;
  const dt = J('#logDateTo')?.value;
  if (s) q.set('q', s);
  if (minc) q.set('min_chars', minc);
  if (maxc) q.set('max_chars', maxc);
  if (act) q.set('action', act);
  if (df) q.set('date_from', df);
  if (dt) q.set('date_to', dt);

  const rows = await jget(API.logs() + (q.toString() ? `?${q.toString()}` : ''));
  const tb = J('#logsTbody'); tb.innerHTML = '';
  for (const x of rows) {
    const tr = document.createElement('tr');
    tr.innerHTML = `
      <td>${x.id}</td>
      <td>${x.license_id ?? ''}</td>
      <td>${x.action}</td>
      <td>${x.char_count ?? 0}</td>
      <td>${x.details ?? ''}</td>
      <td>${x.created_at ?? ''}</td>`;
    tb.appendChild(tr);
  }
}

// === CONFIG ===
async function loadConfig() {
  const cfg = await jget(API.cfg());
  J('#cfgLatest').value = cfg.latest_version || '';
  J('#cfgForce').checked = !!cfg.force_update;
  J('#cfgMaint').checked = !!cfg.maintenance;
  J('#cfgMaintMsg').value = cfg.maintenance_message || '';
  J('#cfgDesc').value = cfg.update_description || '';
  J('#cfgLinks').value = cfg.update_links || '';
}
async function saveConfig() {
  await jput(API.cfg(), {
    latest_version: J('#cfgLatest').value.trim(),
    force_update: J('#cfgForce').checked,
    maintenance: J('#cfgMaint').checked,
    maintenance_message: J('#cfgMaintMsg').value,
    update_description: J('#cfgDesc').value,
    update_links: J('#cfgLinks').value
  });
  alert('✅ Конфігурацію збережено');
}
function downloadBackup() {
  window.location.href = API.bkp();
}
function downloadLicensesBackup() {
  window.location.href = API.bkpLic();
}

// === CONSOLE (/api) ===
async function runConsole() {
  let payload = {};
  try { payload = JSON.parse(J('#apiPayload').value || '{}'); }
  catch { return alert('Невірний JSON'); }
  const r = await jpost(API.console(), payload);
  J('#apiResult').textContent = JSON.stringify(r, null, 2);
}
function formatJson() {
  try {
    const obj = JSON.parse(J('#apiPayload').value || '{}');
    J('#apiPayload').value = JSON.stringify(obj, null, 2);
  } catch {}
}

// === INIT ===
document.addEventListener('DOMContentLoaded', async () => {
  try {
    await Promise.all([loadLicenses(), loadApiKeys(), loadVoices(), loadLogs(), loadConfig()]);
  } catch (e) {
    if (String(e).includes('401')) {
      alert('❌ Неавторизовано. Перезавантаж сторінку — браузер попросить логін/пароль (ADMIN_USER / ADMIN_PASS).');
    } else {
      console.error(e);
      alert('Помилка при завантаженні даних. Перевір консоль браузера.');
    }
  }
});