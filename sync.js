/* Cloud sync for English Trainer through a personal Google Apps Script web app that stores
   progress as a private file in the user's Drive (see apps-script/Code.gs). No OAuth, no tokens.
   Local-first: the app keeps working from localStorage; this module pulls, merges and pushes in the background.
   The "sync code" (web app URL + '#' + secret) is entered once per device and kept in localStorage. */
(function(){
const A = window.__app; if (!A) return;
const CODE = 'bet3.synccode';
const S = window.Sync = { enabled:true, user:null, status:'signed-out', last:null, error:null };
let url = null, key = null, timer = null, busy = false, again = false;
const emit = () => A.onStatus && A.onStatus();
const canon = o => JSON.stringify(o, (k, v) => v && typeof v === 'object' && !Array.isArray(v) ? Object.keys(v).sort().reduce((a, x) => (a[x] = v[x], a), {}) : v);

function parse(code){ const c = String(code || '').trim(), i = c.lastIndexOf('#');
  if (i < 10 || !/^https:\/\/script\.google(usercontent)?\.com\//.test(c)) return false;
  url = c.slice(0, i); key = c.slice(i + 1); return !!key; }
async function call(action, state){
  const r = await fetch(url, { method:'POST', body:JSON.stringify({ key, action, state }) });   // text/plain: no CORS preflight
  if (!r.ok) throw new Error('HTTP ' + r.status);
  const j = await r.json(); if (j.error) throw new Error(j.error); return j; }

S.connect = async code => {
  if (!parse(code)) { S.status = 'error'; S.error = 'Code must look like https://script.google.com/…/exec#your-secret'; return emit(); }
  try { await call('get'); } catch(e){ url = key = null; S.status = 'error'; S.error = e.message === 'wrong key' ? 'Wrong secret' : 'Could not reach the script (' + e.message + ')'; return emit(); }
  try { localStorage.setItem(CODE, JSON.stringify(code.trim())); } catch(e){}
  S.user = {}; S.status = 'idle'; emit(); sync(); };
S.signOut = () => { try { localStorage.removeItem(CODE); } catch(e){} url = key = null; S.user = null; S.status = 'signed-out'; emit(); };
S.schedule = () => { if (!S.user || S.merging) return; clearTimeout(timer); timer = setTimeout(sync, 2500); };
S.now = () => sync();

async function sync(){
  if (!S.user) return;
  if (busy) { again = true; return; }
  busy = true; S.status = 'syncing'; S.error = null; emit();
  try {
    const { state: remote } = await call('get');
    S.merging = true;                                // merge writes to localStorage: must not re-trigger a sync
    let state; try { if (remote) A.mergeState(remote); state = A.getState(); } finally { S.merging = false; }
    if (!remote || canon(remote) !== canon(state)) await call('put', state);
    S.status = 'synced'; S.last = Date.now();
  } catch(e){ S.status = navigator.onLine ? 'error' : 'offline'; S.error = e.message || String(e); }
  busy = false; emit();
  if (again) { again = false; S.schedule(); }
}

try { const c = JSON.parse(localStorage.getItem(CODE)); if (c && parse(c)) { S.user = {}; S.status = 'idle'; sync(); } } catch(e){}
addEventListener('online', () => S.user && sync());
document.addEventListener('visibilitychange', () => { S.user && sync(); });
})();
