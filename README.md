# english-trainer

Business English Trainer, offline-first PWA.

- `/` main app (formerly v2): one Google Sheet `vocabulary_v2`
  - tab `Eng_Phrases` (gid 64343216) -> Phrases & Functions (Mode 1)
  - tab `Eng_Chunks` (gid 2132440094) -> Vocabulary & Chunks (Mode 2)
  - the sheet must stay shared as "Anyone with the link can view"
- `/v1/` archived first version, kept for reference
- `/v2/` redirects to `/`

Progress is kept in the browser (`bet3.*`, v1 under `bet.*`) and can be synced across devices, see below.

## Sync progress across devices

`apps-script/Code.gs` is a small Google Apps Script web app that stores progress in a tab `Progress` of `vocabulary_v2`
(cards, daily log, practice settings). The browser stays the working copy (offline-first); it pushes a few seconds after
each answer and pulls on open, on return to the tab and on reconnect. Cards: newest change wins. Daily log: highest counts win.

1. Open `vocabulary_v2` > Extensions > Apps Script, replace the code with `apps-script/Code.gs`.
2. Change `TOKEN` to a long random string.
3. Deploy > New deployment > type Web app > Execute as: Me > Who has access: Anyone > Deploy. Authorize when asked.
4. Copy the `/exec` URL. In the app: Settings > Sync across devices, paste URL and the same token, Save and sync.
5. Repeat step 4 on every device. After editing the script, use Deploy > Manage deployments > Edit > New version.
