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

## Speak & Record (Mode 3): two paths

- **With my cards**: 4 to 6 targets from both decks, a business scene with four parts, 2 to 3 minutes. Review dates update from how each target was used.
- **Free talk**: any topic (optional topic field and idea chips), no targets, up to 15 minutes, or upload a call/meeting (only the learner is analysed). Same Gemini analysis (audio-tutor rules: patterns before instances, no inflation, hooks, praise as data), no review-date changes. Mistakes go to the error journal with task `Free talk: <topic>`.
- The result screen has **Main menu** next to New set / Talk again.

## AI keys (Mode 3 Speak & Record, Mode 4 Context Drills)

The key lives only in the Script Properties of your Apps Script (`GEMINI_KEY`), never in the repo or the sheet. Use a key from a
Google Cloud project with billing for the app (inputs are not used for training); keep the podcast pipeline on a separate
free-tier project.

Model profiles (Settings > AI coach), cheapest model that does each job well:

| Profile | Writes drill tasks | Checks answers | Listens to speech (Mode 3) |
|---|---|---|---|
| Economy | 2.5 Flash-Lite | 2.5 Flash-Lite | 3.1 Flash-Lite |
| Balanced (default) | 2.5 Flash-Lite | 2.5 Flash | 2.5 Flash |
| Best | 2.5 Flash-Lite | newest Flash | newest Flash |

Thinking is capped (512 tokens for drills, 2048 for speech) because thinking is billed as output. The app estimates spend per
device from token counts (Settings > AI coach). Drill difficulty: B2, B2+ (default), C1; the summary suggests a step up or down.

Every device connected to sync asks the script for the key (action `keys`, protected by the token) and caches them locally.
Rotate the key: change the property, then Settings > AI coach > Reload key from Apps Script. A key typed in Settings on a device
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

## Error journal and Mode 5 · Fix My Errors

Every mistake from Speak & Record (Mode 3) and the first attempt in Context Drills (Mode 4) is saved as one row in the
`Errors` tab of vocabulary_v2 (created by the script): key, date, mode, task, code, type, wrong, fix, why_ru, context,
target, level, status, updated. Rows queue on the device while offline. Speak sessions already stored on a device are
imported once.

Fix My Errors trains one rule at a time. Every error carries a topic id in the `type` column (`ART.a-an-adj`,
`NEG.no-any`, `LEX.make-do-take`; the `code` column is the prefix). There are 42 topics, each one rule a learner can state in
a line; grammar topics are "rule" lessons, collocations, idioms, false friends, calques and terms are "chunks" lessons (a
phrase family, every phrase drilled). The Speak and Drills coaches get the topic list and tag new errors with an id directly.

The bank has two layers. `fixbank.json` in this repo holds the base lesson and 12 tasks (3 of each type) for every topic.
The `FixBank` tab of vocabulary_v2 is a layer on top, one row per topic id: a newer lesson replaces the base one, tasks are
added by id (same id replaces). The `Topics` tab lists the valid ids with title, coach hint, task count and how many errors
the lesson was written from. A scheduled Claude run every 3 days classifies errors that arrived without a valid id (writes
`code` and `type` only), opens a new topic when 3 or more errors share a rule no topic covers, refreshes a lesson when a topic
gains 3 or more new errors, and adds 4 tasks at a time to topics with 5 or more live errors until they have 24.

Topics are listed by priority: open errors weigh more than drilled ones, recent errors more than old ones. Errors with no known
topic fall back to one group per code with a Gemini lesson once a code has 3 of them.

A session is a lesson plus 8 tasks from easy to hard: 2 choose, 2 fill the gap, 2 fix the mistake, 2 translate, unseen
tasks first. 7 of 8 marks the topic's errors as drilled. On a later day, Mixed review shuffles production tasks (fill the
gap, fix, translate) from up to 4 drilled topics with no label saying which rule applies; the Rule button reveals it. A topic
whose tasks are all right moves its drilled errors to fixed; a missed topic goes back to open for a fresh lesson. A plain
7 of 8 on the same topic on another day also marks it fixed. Exact answers are checked in the app, others by Gemini.