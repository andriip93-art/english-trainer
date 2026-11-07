# english-trainer

Business English Trainer, offline-first PWA.

- `/` main app (formerly v2): one Google Sheet `vocabulary_v2`
  - tab `Eng_Phrases` (gid 64343216) -> Phrases & Functions (Mode 1)
    columns: `#`, `Universal Phrase`, `Native Translation (RU)`, `Category`, `Strategic Intent (RU)`, `Dialogues`,
    `Alternatives` (other ways to say it, separated by ` | `), `Status` (`Active` = core set, `Passive` = extended, `Drop` = hidden)
  - tab `Eng_Phrases_archive` keeps the full original 694-phrase list (not read by the app)
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
2. Project Settings (gear) > Script Properties: add `TOKEN` (a long random string). If you used the old version with the token
   written in the code, copy that same value into the property, so connected devices keep working.
3. Deploy > New deployment > type Web app > Execute as: Me > Who has access: Anyone > Deploy. Authorize when asked.
   Updating an existing deployment: Deploy > Manage deployments > Edit (pencil) > Version: New version > Deploy (the URL stays the same).
4. Copy the `/exec` URL. In the app: Settings > Sync across devices, paste URL and the same token, Save and sync.
5. On every other device: open Settings > Copy setup link for another device on a connected device, send the link to yourself
   and open it on the new device (or repeat step 4 by hand).

## AI keys (Mode 3 Speak & Record, Mode 4 Context Drills)

Keys live only in the Script Properties of your Apps Script, never in the repo or the sheet:

- `GEMINI_KEY`: Gemini API key. Use a key from a Google Cloud project with billing for the app (inputs are not used for training).
  Keep the podcast pipeline on a separate free-tier project.
- `GROQ_KEY` (optional): backup provider, text-only analysis.

Every device connected to sync asks the script for the keys (action `keys`, protected by the token) and caches them locally.
Rotate a key: change the property, then Settings > AI coach > Reload keys from Apps Script. A key typed in Settings on a device
overrides the script for that device only. In Google Cloud > Credentials restrict the Gemini key to the Generative Language API
and to the site address `https://andriip93-art.github.io/*`.

## Mode 4 · Context Drills

Pushed written output with a coach. Targets come from both decks, weighted to due and weak cards. Task types:
Respond (reply to a work moment, a function phrase is paired with a content chunk), Translate (Russian cue to natural English,
the target is hidden), Upgrade (rewrite a blunt or calqued line), Create (own sentence), Mix (interleaved). Two graded hints per
item. Feedback: grade A to D, target status, tappable error and success highlights, a minimal fix, a native executive version,
one rule per error with the same interference codes as Mode 3, one rewrite per item. First-attempt grade updates review dates
(A/B = Good, C or any hint = Hard, avoided or D = back tomorrow). Error codes from drills and speaking add up to a personal
pattern list on the start screen. Dictation uses the browser's speech recognition where available.
