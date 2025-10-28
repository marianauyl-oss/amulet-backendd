// ---- helpers ----
async function jfetch(url, method="GET", data=null) {
  const opt = { method, headers: { "Content-Type":"application/json" } };
  if (data) opt.body = JSON.stringify(data);
  const r = await fetch(url, opt);
  if (!r.ok) throw new Error(`${r.status} ${r.statusText}`);
  return await r.json();
}
function el(id){ return document.getElementById(id); }
function toast(msg){ alert(msg); }

function copyToClipboard(text) {
  navigator.clipboard.writeText(text).then(
    () => toast("Скопійовано: " + text),
    (err) => toast("Помилка копіювання: " + err)
  );
}
function escapeHTML(s){ return (s ?? '').toString()
  .replace(/&/g,'&amp;').replace(/</g,'&lt;')
  .replace(/>/g,'&gt;').replace(/"/g,'&quot;')
  .replace(/'/g,'&#39;'); }

// ================= Licenses =================
let currentLicEditId = null;

async function loadLicenses(){
  try{
    const q = encodeURIComponent(el("licSearch").value || "");
    const minCredit = el("licMinCredit").value || "";
    const maxCredit = el("licMaxCredit").value || "";
    const active = el("licActiveFilter").value || "";
    const dateFrom = el("licDateFrom").value || "";
    const dateTo = el("licDateTo").value || "";
    let url = `/admin_api/licenses?q=${q}`;
    if (minCredit) url += `&min_credit=${minCredit}`;
    if (maxCredit) url += `&max_credit=${maxCredit}`;
    if (active) url += `&active=${active}`;
    if (dateFrom) url += `&date_from=${dateFrom}`;
    if (dateTo) url += `&date_to=${dateTo}`;

    const data = await jfetch(url);
    const tb = el("licTbody");
    tb.innerHTML = "";
    data.forEach(row=>{
      const tr = document.createElement("tr");
      tr.innerHTML = `
        <td>${row.id}</td>
        <td><code class="copyable" data-copy="${escapeHTML(row.key)}">${escapeHTML(row.key)}</code></td>
        <td>${escapeHTML(row.mac_id || "")}</td>
        <td><strong>${row.credit}</strong></td>
        <td>${row.active ? "Active" : "Inactive"}</td>
        <td class="small">${row.created_at ? new Date(row.created_at).toLocaleString() : ""}</td>
        <td class="small">${row.updated_at ? new Date(row.updated_at).toLocaleString() : ""}</td>
        <td class="text-nowrap">
          <button class="btn btn-sm btn-outline-primary me-1 edit-lic" data-id="${row.id}">✏️</button>
          <button class="btn btn-sm btn-outline-warning me-1 toggle-lic" data-id="${row.id}">🔁</button>
          <button class="btn btn-sm btn-outline-danger del-lic" data-id="${row.id}">🗑</button>
        </td>`;
      tb.appendChild(tr);

      tr.querySelector('.edit-lic').addEventListener('click', ()=>{
        editLicense(row.id, row.key, row.mac_id || "", row.credit, row.active);
      });
      tr.querySelector('.toggle-lic').addEventListener('click', ()=> toggleLicense(row.id));
      tr.querySelector('.del-lic').addEventListener('click', ()=> deleteLicense(row.id));
    });
    tb.querySelectorAll('.copyable').forEach(n=>{
      n.addEventListener('click', ()=> copyToClipboard(n.dataset.copy));
    });
  }catch(e){ toast("Load licenses error: "+e.message); }
}

function resetLicenseForm(){
  currentLicEditId = null;
  el("licFormTitle").textContent = "Додати ліцензію";
  el("licId").value = "";
  el("licKey").value = "";
  el("licMac").value = "";
  el("licCredit").value = "0";
  el("licActive").checked = true;
  el("licDelta").value = "";
}

function editLicense(id,key,mac,credit,active){
  currentLicEditId = id;
  el("licFormTitle").textContent = `Редагувати #${id}`;
  el("licId").value = id;
  el("licKey").value = key;
  el("licMac").value = mac || "";
  el("licCredit").value = credit;
  el("licActive").checked = !!active;
}

async function submitLicense(){
  const payload = {
    key: el("licKey").value.trim(),
    mac_id: el("licMac").value.trim(),
    credit: Number(el("licCredit").value||0),
    active: el("licActive").checked
  };
  try{
    if (currentLicEditId){
      await jfetch(`/admin_api/licenses/${currentLicEditId}`, "PUT", payload);
    } else {
      await jfetch(`/admin_api/licenses`, "POST", payload);
    }
    resetLicenseForm();
    await loadLicenses();
  }catch(e){ toast("Save license error: "+e.message); }
}

async function deleteLicense(id){
  if (!confirm("Видалити ліцензію?")) return;
  try{
    await jfetch(`/admin_api/licenses/${id}`, "DELETE");
    await loadLicenses();
  }catch(e){ toast("Delete error: "+e.message); }
}

async function toggleLicense(id){
  try{
    await jfetch(`/admin_api/licenses/${id}/toggle`, "POST", {});
    await loadLicenses();
  }catch(e){ toast("Toggle error: "+e.message); }
}

async function applyDelta(){
  const id = Number(el("licId").value || 0);
  if (!id){ toast("Спочатку вибери ліцензію (кнопка ✏️)"); return; }
  const delta = Number(el("licDelta").value||0);
  try{
    const res = await jfetch(`/admin_api/licenses/${id}/credit`, "POST", { delta });
    toast("New credit: "+res.credit);
    el("licDelta").value = "";
    el("licCredit").value = res.credit;
    await loadLicenses();
  }catch(e){ toast("Δ error: "+e.message); }
}

// ================= API Keys =================
let currentKeyEditId = null;

async function loadApiKeys(){
  try{
    const data = await jfetch(`/admin_api/apikeys`);
    const tb = el("keysTbody");
    tb.innerHTML = "";
    data.forEach(row=>{
      const tr = document.createElement("tr");
      tr.innerHTML = `
        <td>${row.id}</td>
        <td><code class="copyable" data-copy="${escapeHTML(row.api_key)}">${escapeHTML(row.api_key)}</code></td>
        <td>${escapeHTML(row.status)}</td>
        <td class="text-nowrap">
          <button class="btn btn-sm btn-outline-primary me-1 edit-key" data-id="${row.id}">✏️</button>
          <button class="btn btn-sm btn-outline-danger del-key" data-id="${row.id}">🗑</button>
        </td>`;
      tb.appendChild(tr);

      tr.querySelector('.edit-key').addEventListener('click', ()=>{
        editApiKey(row.id, row.api_key, row.status);
      });
      tr.querySelector('.del-key').addEventListener('click', ()=> deleteApiKey(row.id));
    });
    tb.querySelectorAll('.copyable').forEach(n=>{
      n.addEventListener('click', ()=> copyToClipboard(n.dataset.copy));
    });
  }catch(e){ toast("Load apikeys error: "+e.message); }
}

function resetKeyForm(){
  currentKeyEditId = null;
  el("keyFormTitle").textContent = "Додати API ключ";
  el("keyId").value = "";
  el("keyValue").value = "";
  el("keyStatus").value = "active";
}

function editApiKey(id,api_key,status){
  currentKeyEditId = id;
  el("keyFormTitle").textContent = `Редагувати API ключ #${id}`;
  el("keyId").value = id;
  el("keyValue").value = api_key;
  el("keyStatus").value = status;
}

async function submitApiKey(){
  const payload = {
    api_key: el("keyValue").value.trim(),
    status: el("keyStatus").value
  };
  try{
    if (currentKeyEditId){
      await jfetch(`/admin_api/apikeys/${currentKeyEditId}`, "PUT", payload);
    } else {
      await jfetch(`/admin_api/apikeys`, "POST", payload);
    }
    resetKeyForm();
    await loadApiKeys();
  }catch(e){ toast("Save apikey error: "+e.message); }
}

async function deleteApiKey(id){
  if (!confirm("Видалити API ключ?")) return;
  try{
    await jfetch(`/admin_api/apikeys/${id}`, "DELETE");
    await loadApiKeys();
  }catch(e){ toast("Delete apikey error: "+e.message); }
}

// ================= Voices =================
let currentVoiceEditId = null;

async function loadVoices(){
  try{
    const data = await jfetch(`/admin_api/voices`);
    const tb = el("voicesTbody");
    tb.innerHTML = "";
    data.forEach(row=>{
      const tr = document.createElement("tr");
      tr.innerHTML = `
        <td>${row.id}</td>
        <td>${escapeHTML(row.name)}</td>
        <td><code class="copyable" data-copy="${escapeHTML(row.voice_id)}">${escapeHTML(row.voice_id)}</code></td>
        <td>${row.active ? "Active" : "Inactive"}</td>
        <td class="text-nowrap">
          <button class="btn btn-sm btn-outline-primary me-1 edit-voice" data-id="${row.id}">✏️</button>
          <button class="btn btn-sm btn-outline-danger del-voice" data-id="${row.id}">🗑</button>
        </td>`;
      tb.appendChild(tr);

      tr.querySelector('.edit-voice').addEventListener('click', ()=>{
        editVoice(row.id, row.name, row.voice_id, row.active);
      });
      tr.querySelector('.del-voice').addEventListener('click', ()=> deleteVoice(row.id));
    });
    tb.querySelectorAll('.copyable').forEach(n=>{
      n.addEventListener('click', ()=> copyToClipboard(n.dataset.copy));
    });
  }catch(e){ toast("Load voices error: "+e.message); }
}

function resetVoiceForm(){
  currentVoiceEditId = null;
  el("voiceFormTitle").textContent = "Додати голос";
  el("voiceId").value = "";
  el("voiceName").value = "";
  el("voiceValue").value = "";
  el("voiceActive").checked = true;
  el("voiceFile").value = "";
}

function editVoice(id,name,voice_id,active){
  currentVoiceEditId = id;
  el("voiceFormTitle").textContent = `Редагувати голос #${id}`;
  el("voiceId").value = id;
  el("voiceName").value = name;
  el("voiceValue").value = voice_id;
  el("voiceActive").checked = !!active;
}

async function submitVoice(){
  const payload = {
    name: el("voiceName").value.trim(),
    voice_id: el("voiceValue").value.trim(),
    active: el("voiceActive").checked
  };
  try{
    if (currentVoiceEditId){
      await jfetch(`/admin_api/voices/${currentVoiceEditId}`, "PUT", payload);
    } else {
      await jfetch(`/admin_api/voices`, "POST", payload);
    }
    resetVoiceForm();
    await loadVoices();
  }catch(e){ toast("Save voice error: "+e.message); }
}

async function uploadVoices(){
  const fileInput = el("voiceFile");
  if (!fileInput.files.length){
    toast("Оберіть файл .txt");
    return;
  }
  const formData = new FormData();
  formData.append("file", fileInput.files[0]);
  try{
    const res = await fetch("/admin_api/voices/upload", { method: "POST", body: formData });
    const data = await res.json();
    if (!res.ok) throw new Error(data.msg || "Upload error");
    toast(`Успішно додано ${data.added} голосів`);
    resetVoiceForm();
    await loadVoices();
  }catch(e){
    toast("Upload voices error: "+e.message);
  }
}

async function deleteVoice(id){
  if (!confirm("Видалити голос?")) return;
  try{
    await jfetch(`/admin_api/voices/${id}`, "DELETE");
    await loadVoices();
  }catch(e){ toast("Delete voice error: "+e.message); }
}

// ================= Activity Logs =================
async function loadLogs(){
  try{
    const q = encodeURIComponent(el("logSearch").value || "");
    const minChars = el("logMinChars").value || "";
    const maxChars = el("logMaxChars").value || "";
    const action = el("logAction").value || "";
    const dateFrom = el("logDateFrom").value || "";
    const dateTo = el("logDateTo").value || "";
    let url = `/admin_api/logs?q=${q}`;
    if (minChars) url += `&min_chars=${minChars}`;
    if (maxChars) url += `&max_chars=${maxChars}`;
    if (action) url += `&action=${action}`;
    if (dateFrom) url += `&date_from=${dateFrom}`;
    if (dateTo) url += `&date_to=${dateTo}`;
    
    const data = await jfetch(url);
    const tb = el("logsTbody");
    tb.innerHTML = "";
    data.forEach(row=>{
      const tr = document.createElement("tr");
      tr.innerHTML = `
        <td>${row.id}</td>
        <td>${row.license_id ?? ""}</td>
        <td>${escapeHTML(row.action)}</td>
        <td>${row.char_count ?? ""}</td>
        <td>${escapeHTML(row.details ?? "")}</td>
        <td class="small">${row.created_at ? new Date(row.created_at).toLocaleString() : ""}</td>`;
      tb.appendChild(tr);
    });
  }catch(e){ toast("Load logs error: "+e.message); }
}

// ================= Config =================
async function loadConfig(){
  try{
    const c = await jfetch(`/admin_api/config`);
    el("cfgLatest").value = c.latest_version || "";
    el("cfgForce").checked = !!c.force_update;
    el("cfgMaint").checked = !!c.maintenance;
    el("cfgMaintMsg").value = c.maintenance_message || "";
    el("cfgDesc").value = c.update_description || "";
    el("cfgLinks").value = c.update_links || "";
  }catch(e){ toast("Load config error: "+e.message); }
}

async function saveConfig(){
  try{
    await jfetch(`/admin_api/config`, "PUT", {
      latest_version: el("cfgLatest").value.trim(),
      force_update: el("cfgForce").checked,
      maintenance: el("cfgMaint").checked,
      maintenance_message: el("cfgMaintMsg").value,
      update_description: el("cfgDesc").value,
      update_links: el("cfgLinks").value
    });
    toast("Збережено ✅");
  }catch(e){ toast("Save config error: "+e.message); }
}

async function downloadBackup(){
  try{
    const res = await fetch("/admin_api/backup");
    if (!res.ok) throw new Error("Backup download failed");
    const blob = await res.blob();
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    const cd = res.headers.get("Content-Disposition") || "";
    const fn = (cd.split("filename=")[1] || "amulet_backup.json").replace(/"/g,"");
    a.download = fn;
    a.click();
    window.URL.revokeObjectURL(url);
  }catch(e){
    toast("Backup error: "+e.message);
  }
}

async function downloadLicensesBackup(){
  try{
    const res = await fetch("/admin_api/backup/licenses");
    if (!res.ok) throw new Error("Licenses backup download failed");
    const blob = await res.blob();
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    const cd = res.headers.get("Content-Disposition") || "";
    const fn = (cd.split("filename=")[1] || "amulet_licenses_backup.json").replace(/"/g,"");
    a.download = fn;
    a.click();
    window.URL.revokeObjectURL(url);
  }catch(e){
    toast("Licenses backup error: "+e.message);
  }
}

// ================= API Console =================
function formatJson(){
  try{
    const obj = JSON.parse(el("apiPayload").value || "{}");
    el("apiPayload").value = JSON.stringify(obj, null, 2);
  }catch(e){ toast("JSON invalid"); }
}

async function runConsole(){
  try{
    const action = (el("apiAction").value || "").trim();
    const payload = (el("apiPayload").value || "{}").trim();
    const body = payload ? JSON.parse(payload) : {};
    if (action) body.action = action;
    const res = await jfetch("/api", "POST", body);
    el("apiResult").textContent = JSON.stringify(res, null, 2);
  }catch(e){ el("apiResult").textContent = "Error: "+e.message; }
}

// ---- on load ----
window.addEventListener("DOMContentLoaded", async ()=>{
  await Promise.all([loadLicenses(), loadApiKeys(), loadVoices(), loadConfig(), loadLogs()]);
});