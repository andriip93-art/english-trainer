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
 * Setup: set TOKEN below, then Deploy > New deployment > Web app,
 *        Execute as: Me, Who has access: Anyone. Copy the /exec URL into the app (Settings > Sync).
 */
const TOKEN = 'CHANGE_ME_TO_A_LONG_RANDOM_STRING';
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
  const lock = LockService.getScriptLock();
  lock.waitLock(25000);
  try {
    const req = JSON.parse(e.postData.contents);
    if (req.token !== TOKEN) return json_({ error: 'bad token' });
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
