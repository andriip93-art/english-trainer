/**
 * Business English Trainer: progress sync backend.
 * Lives inside the vocabulary_v2 spreadsheet (Extensions > Apps Script) and keeps one tab, "Progress".
 *
 * Tab layout (created automatically): key | json | u | sv
 *   c|<deck>|<id>   one spaced-repetition card        (last write wins, by u = card update time)
 *   l|<YYYY-MM-DD>  one day of the activity log        (merged field by field, highest number wins)
 *   g               synced settings                    (last write wins)
 *   sv = server time of the last change, used so each device only downloads what is new.
 *
 * Setup: Project Settings > Script Properties, add:
 *          TOKEN       a long random string (the app asks for it once per device)
 *          GEMINI_KEY  your Gemini API key (paid project: no training on your data)   optional
 *          GROQ_KEY    your Groq API key (backup for text analysis)                    optional
 *        Then Deploy > New deployment > Web app, Execute as: Me, Who has access: Anyone.
 *        Copy the /exec URL into the app (Settings > Sync). After editing this file later use
 *        Deploy > Manage deployments > Edit > Version: New version, so the URL stays the same.
 *
 * Key vault: action "keys" hands the AI keys to a device that knows the TOKEN, so each phone or laptop
 * gets them automatically and nobody types a key twice. Keys never live in the repo or in the sheet.
 */
const TOKEN_FALLBACK = 'CHANGE_ME_TO_A_LONG_RANDOM_STRING';   // used only if the TOKEN script property is not set
function token_() { return PropertiesService.getScriptProperties().getProperty('TOKEN') || TOKEN_FALLBACK; }
const TAB = 'Progress';

function tab_() {
  const ss = SpreadsheetApp.getActive();
  let s = ss.getSheetByName(TAB);
  if (!s) {
    s = ss.insertSheet(TAB);
    s.appendRow(['key', 'json', 'u', 'sv']);
    s.setFrozenRows(1);
  }
  return s;
}

function json_(o) {
  return ContentService.createTextOutput(JSON.stringify(o)).setMimeType(ContentService.MimeType.JSON);
}

function maxMerge_(a, b) {
  let x = {}, y = {};
  try { x = JSON.parse(a) || {}; } catch (e) {}
  try { y = JSON.parse(b) || {}; } catch (e) {}
  Object.keys(y).forEach(function (f) { x[f] = Math.max(Number(x[f]) || 0, Number(y[f]) || 0); });
  return JSON.stringify(x);
}

function doGet() {
  return json_({ ok: true, service: 'english-trainer-progress' });
}

function doPost(e) {
  let req;
  try { req = JSON.parse(e.postData.contents); } catch (err) { return json_({ error: 'bad request' }); }
  if (!req || req.token !== token_() || token_() === 'CHANGE_ME_TO_A_LONG_RANDOM_STRING') { Utilities.sleep(800); return json_({ error: 'bad token' }); }

  if (req.action === 'keys') {
    const p = PropertiesService.getScriptProperties();
    return json_({ ok: true, gemini: p.getProperty('GEMINI_KEY') || '', groq: p.getProperty('GROQ_KEY') || '' });
  }

  const lock = LockService.getScriptLock();
  lock.waitLock(25000);
  try {
    const s = tab_();
    const now = Date.now();

    if (req.action === 'wipe') {
      const n = s.getLastRow() - 1;
      if (n > 0) s.getRange(2, 1, n, 4).clearContent();
      return json_({ ok: true, now: now, rows: [] });
    }

    const last = s.getLastRow();
    const data = last > 1 ? s.getRange(2, 1, last - 1, 4).getValues() : [];
    const idx = {};
    data.forEach(function (r, i) { idx[r[0]] = i; });
    let dirty = false;

    (req.items || []).forEach(function (it) {
      if (!it || typeof it.k !== 'string' || typeof it.j !== 'string') return;
      const i = idx[it.k];
      if (i === undefined) {
        idx[it.k] = data.length;
        data.push([it.k, it.j, Number(it.u) || 0, now]);
        dirty = true;
        return;
      }
      const row = data[i];
      if (it.k.indexOf('l|') === 0) {
        const merged = maxMerge_(row[1], it.j);
        if (merged !== row[1]) { row[1] = merged; row[2] = Math.max(Number(row[2]) || 0, Number(it.u) || 0); row[3] = now; dirty = true; }
      } else if ((Number(it.u) || 0) > (Number(row[2]) || 0)) {
        row[1] = it.j; row[2] = Number(it.u); row[3] = now; dirty = true;
      }
    });

    if (dirty) s.getRange(2, 1, data.length, 4).setValues(data);

    const since = Number(req.since) || 0;
    const rows = data
      .filter(function (r) { return r[0] && Number(r[3]) >= since; })
      .map(function (r) { return { k: r[0], j: String(r[1]), u: Number(r[2]) }; });
    return json_({ ok: true, now: now, rows: rows });
  } catch (err) {
    return json_({ error: String(err) });
  } finally {
    lock.releaseLock();
  }
}
