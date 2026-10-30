// English Trainer sync backend. Paste into script.google.com, set SECRET, deploy as a Web app
// (Execute as: Me, Who has access: Anyone). Progress is stored in your Drive as a private file.
const SECRET = 'PUT-YOUR-OWN-SECRET-HERE';
const FILE = 'english-trainer-progress.json';

function file_() {
  const it = DriveApp.getFilesByName(FILE);
  return it.hasNext() ? it.next() : DriveApp.createFile(FILE, 'null', 'application/json');
}
function out_(o) {
  return ContentService.createTextOutput(JSON.stringify(o)).setMimeType(ContentService.MimeType.JSON);
}
function doGet() { return out_({ ok: true, app: 'english-trainer-sync' }); }
function doPost(e) {
  let q;
  try { q = JSON.parse(e.postData.contents); } catch (err) { return out_({ error: 'bad request' }); }
  if (q.key !== SECRET) return out_({ error: 'wrong key' });
  const lock = LockService.getScriptLock();
  lock.waitLock(20000);
  try {
    const f = file_();
    if (q.action === 'put') { f.setContent(JSON.stringify(q.state)); return out_({ ok: true }); }
    return out_({ state: JSON.parse(f.getBlob().getDataAsString() || 'null') });
  } finally { lock.releaseLock(); }
}
