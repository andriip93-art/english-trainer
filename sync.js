/* Cloud sync for English Trainer via the user's own Google Drive (hidden appDataFolder).
   Local-first: the app keeps working from localStorage; this module only pulls, merges and pushes
   in the background. Without SYNC_CFG.clientId it does nothing.
   Browser-only Google sign-in gives 1-hour tokens and no refresh token, so after a while the next
   sync asks Google again (silent if possible, otherwise on the next "Sync now" tap). */
(function(){
const CFG = window.SYNC_CFG || {};
const A = window.__app;
if (!CFG.clientId || !A) { window.Sync = { enabled:false }; return; }

const GIS = 'https://accounts.google.com/gsi/client';
const SCOPE = 'https://www.googleapis.com/auth/drive.appdata';
const FILE = 'progress.json', TK = 'bet3.gtoken', FLAG = 'bet3.gsignedin';
const S = window.Sync = { enabled:true, user:null, status:'signed-out', last:null, error:null };
let tc = null, token = null, exp = 0, fileId = null, timer = null, busy = false, again = false;
const emit = () => A.onStatus && A.onStatus();
const canon = o => JSON.stringify(o, (k, v) => v && typeof v === 'object' && !Array.isArray(v) ? Object.keys(v).sort().reduce((a, x) => (a[x] = v[x], a), {}) : v);
const lsGet = k => { try { return JSON.parse(localStorage.getItem(k)); } catch(e){ return null; } };
const lsSet = (k, v) => { try { v == null ? localStorage.removeItem(k) : localStorage.setItem(k, JSON.stringify(v)); } catch(e){} };

function loadLib(){ return new Promise((res, rej) => {
  if (window.google?.accounts?.oauth2) return res();
  const s = document.createElement('script'); s.src = GIS; s.async = true; s.onload = res; s.onerror = () => rej(new Error('offline')); document.head.appendChild(s); }); }

function getToken(interactive){ return new Promise((res, rej) => {
  if (token && Date.now() < exp - 60000) return res(token);
  if (!tc) tc = google.accounts.oauth2.initTokenClient({ client_id:CFG.clientId, scope:SCOPE, callback:()=>{}, error_callback:()=>{} });
  tc.callback = r => { if (r.error) return rej(new Error(r.error)); token = r.access_token; exp = Date.now() + (r.expires_in || 3600) * 1000; lsSet(TK, {t:token, exp}); lsSet(FLAG, 1); res(token); };
  tc.error_callback = e => rej(new Error(e.type || 'auth'));
  tc.requestAccessToken({ prompt: interactive ? '' : 'none' }); }); }

async function api(path, opt = {}, retry = true){
  const r = await fetch(path, { ...opt, headers:{ ...(opt.headers||{}), Authorization:'Bearer ' + token } });
  if (r.status === 401 && retry) { token = null; await getToken(false); return api(path, opt, false); }
  if (!r.ok) throw new Error('Drive ' + r.status);
  return r; }

async function findFile(){
  if (fileId) return fileId;
  const q = encodeURIComponent(`name='${FILE}'`);
  const r = await api(`https://www.googleapis.com/drive/v3/files?spaces=appDataFolder&q=${q}&fields=files(id)&orderBy=modifiedTime desc`);
  fileId = (await r.json()).files?.[0]?.id || null; return fileId; }
async function readRemote(){ const id = await findFile(); if (!id) return null;
  return (await api(`https://www.googleapis.com/drive/v3/files/${id}?alt=media`)).json(); }
async function writeRemote(state){
  const id = await findFile(), body = JSON.stringify(state);
  if (id) { await api(`https://www.googleapis.com/upload/drive/v3/files/${id}?uploadType=media`, { method:'PATCH', headers:{'Content-Type':'application/json'}, body }); return; }
  const b = 'bet' + Date.now(), meta = JSON.stringify({ name:FILE, parents:['appDataFolder'] });
  const r = await api('https://www.googleapis.com/upload/drive/v3/files?uploadType=multipart&fields=id', { method:'POST', headers:{'Content-Type':'multipart/related; boundary=' + b },
    body:`--${b}\r\nContent-Type: application/json\r\n\r\n${meta}\r\n--${b}\r\nContent-Type: application/json\r\n\r\n${body}\r\n--${b}--` });
  fileId = (await r.json()).id; }

S.signIn = async () => { try { await loadLib(); await getToken(true); S.user = {}; S.status = 'idle'; emit(); sync(true); } catch(e){ S.status = 'error'; S.error = e.message; emit(); } };
S.signOut = () => { try { if (token) google.accounts.oauth2.revoke(token); } catch(e){} token = null; exp = 0; fileId = null; lsSet(TK, null); lsSet(FLAG, null); S.user = null; S.status = 'signed-out'; emit(); };
S.schedule = () => { if (!S.user || S.merging) return; clearTimeout(timer); timer = setTimeout(() => sync(false), 2500); };
S.now = () => sync(true);

async function sync(interactive){
  if (!S.user) return;
  if (busy) { again = true; return; }
  busy = true; S.status = 'syncing'; S.error = null; emit();
  try {
    try { await loadLib(); await getToken(!!interactive); }
    catch(e){ S.status = navigator.onLine ? 'reconnect' : 'offline'; busy = false; return emit(); }
    const remote = await readRemote();
    S.merging = true;                                // merge writes to localStorage: must not re-trigger a sync
    let state; try { if (remote) A.mergeState(remote); state = A.getState(); } finally { S.merging = false; }
    if (!remote || canon(remote) !== canon(state)) await writeRemote(state);
    S.status = 'synced'; S.last = Date.now();
  } catch(e){ S.status = navigator.onLine ? 'error' : 'offline'; S.error = e.message || String(e); }
  busy = false; emit();
  if (again) { again = false; S.schedule(); }
}

// Resume: a stored token may still be valid; otherwise the first sync tries silently.
if (lsGet(FLAG)) { const t = lsGet(TK); if (t && Date.now() < t.exp - 60000) { token = t.t; exp = t.exp; } S.user = {}; S.status = 'idle'; sync(false); }
addEventListener('online', () => S.user && sync(false));
document.addEventListener('visibilitychange', () => { S.user && sync(false); });
})();
