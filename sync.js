/* Cloud sync for English Trainer (Supabase + Google sign-in).
   Local-first: the app keeps working from localStorage; this module only
   pulls, merges and pushes in the background. Without SYNC_CFG it does nothing. */
(function(){
const CFG = window.SYNC_CFG || {};
const SB_SRC = 'https://cdn.jsdelivr.net/npm/@supabase/supabase-js@2.45.4/dist/umd/supabase.min.js';
const A = window.__app;                       // bridge exposed by index.html
if (!CFG.url || !CFG.anonKey || !A) { window.Sync = { enabled:false }; return; }

const S = window.Sync = { enabled:true, user:null, status:'signed-out', last:null, error:null };
let sb = null, timer = null, busy = false, again = false;
const canon = o => JSON.stringify(o, (k, v) => v && typeof v === 'object' && !Array.isArray(v) ? Object.keys(v).sort().reduce((a, x) => (a[x] = v[x], a), {}) : v);
const emit = () => A.onStatus && A.onStatus();

function loadLib(){ return new Promise((res, rej) => {
  if (window.supabase) return res();
  const s = document.createElement('script'); s.src = SB_SRC; s.onload = res; s.onerror = () => rej(new Error('offline')); document.head.appendChild(s); }); }

async function init(){
  try { await loadLib(); } catch(e){ S.status = 'offline'; return emit(); }
  sb = window.supabase.createClient(CFG.url, CFG.anonKey, { auth:{ flowType:'pkce', persistSession:true, autoRefreshToken:true, detectSessionInUrl:true } });
  sb.auth.onAuthStateChange((ev, session) => { S.user = session?.user || null; S.status = S.user ? 'idle' : 'signed-out'; emit(); if (S.user && (ev==='SIGNED_IN'||ev==='INITIAL_SESSION')) sync(); });
  const { data } = await sb.auth.getSession(); S.user = data.session?.user || null; S.status = S.user ? 'idle' : 'signed-out'; emit();
}

S.signIn  = () => sb && sb.auth.signInWithOAuth({ provider:'google', options:{ redirectTo: location.origin + location.pathname } });
S.signOut = async () => { await sb?.auth.signOut(); S.user = null; S.status = 'signed-out'; emit(); };
S.schedule = () => { if (!S.user || S.merging) return; clearTimeout(timer); timer = setTimeout(sync, 2500); };
S.now = () => sync();

async function sync(){
  if (!sb || !S.user) return;
  if (busy) { again = true; return; }
  busy = true; S.status = 'syncing'; S.error = null; emit();
  try {
    for (let attempt = 0; attempt < 4; attempt++) {
      const { data: row, error } = await sb.from('progress').select('state,version').eq('user_id', S.user.id).maybeSingle();
      if (error) throw error;
      // merge remote into local (never loses either side), then push the union
      S.merging = true;                              // merge writes to localStorage: must not re-trigger a sync
      let state; try { if (row) A.mergeState(row.state || {}); state = A.getState(); } finally { S.merging = false; }
      if (row && canon(row.state) === canon(state)) break;   // nothing new to push
      if (!row) {
        const { error: e } = await sb.from('progress').insert({ user_id:S.user.id, state, version:1 });
        if (e && e.code === '23505') continue;      // other device inserted first: re-pull and merge
        if (e) throw e; break;
      }
      const { data: upd, error: e } = await sb.from('progress').update({ state, version: row.version + 1 })
        .eq('user_id', S.user.id).eq('version', row.version).select('version');
      if (e) throw e;
      if (upd && upd.length) break;                  // success; otherwise another device won: loop
    }
    S.status = 'synced'; S.last = Date.now();
  } catch(e){ S.status = navigator.onLine ? 'error' : 'offline'; S.error = e.message || String(e); }
  busy = false; emit();
  if (again) { again = false; S.schedule(); }
}

addEventListener('online', () => S.user && sync());
document.addEventListener('visibilitychange', () => { S.user && sync(); });
init();
})();
