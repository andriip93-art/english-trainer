# english-trainer

Business English Trainer, offline-first PWA.

- `/` main app (formerly v2): vocabulary from the Google Sheet `vocabulary_v2`, phrases from the published phrases sheet
- `/v1/` archived first version, kept for reference
- `/v2/` redirects to `/`

Progress is stored per browser: main app under `bet3.*`, v1 under `bet.*`.

## Cloud sync (your Google Drive via Apps Script)

Progress (cards, daily log, bullet records) syncs between devices through a private file in your own Google Drive.
A tiny Google Apps Script web app (`apps-script/Code.gs`) reads and writes it. No Google Cloud project, no OAuth, no tokens that expire.
The app stays local-first and works offline. Merge rules: newer review wins per card, daily counters and best scores take the max,
"Erase all progress" is propagated via a `wipedAt` marker. Sheet sources, theme and other settings are not synced.

One-time setup (about 5 minutes):

1. Open script.google.com -> New project. Replace the code with `apps-script/Code.gs`.
2. Change `SECRET` to a password you make up (letters and digits).
3. Deploy -> New deployment -> type **Web app**. Execute as: **Me**. Who has access: **Anyone**. Deploy and allow access
   (Advanced -> Go to project (unsafe) -> Allow; Google warns because the script is yours and unverified).
4. Copy the Web app URL (ends with `/exec`). Your sync code is that URL, then `#`, then your secret:
   `https://script.google.com/macros/s/.../exec#my-secret`
5. In the app: Settings -> Cloud sync -> paste the code -> Connect. Do the same on every device (first on the one with the most progress).

The secret is checked by the script, so the URL alone cannot read or change your progress. Keep the sync code private and do not commit it.
If you change the script code later, use Deploy -> Manage deployments -> Edit -> New version (the URL stays the same).
