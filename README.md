# english-trainer

Business English Trainer, offline-first PWA.

- `/` main app (formerly v2): vocabulary from the Google Sheet `vocabulary_v2`, phrases from the published phrases sheet
- `/v1/` archived first version, kept for reference
- `/v2/` redirects to `/`

Progress is stored per browser: main app under `bet3.*`, v1 under `bet.*`.

## Cloud sync (your Google Drive)

Progress (cards, daily log, bullet records) syncs between devices through a hidden file in your own Google Drive
(`appDataFolder`, visible only to this app, scope `drive.appdata`). The app stays local-first and works offline.
Merge rules: newer review wins per card, daily counters and best scores take the max, "Erase all progress"
is propagated via a `wipedAt` marker. Sheet sources, theme and other settings are not synced.

One-time setup (about 5 minutes):

1. Google Cloud Console -> create a project -> APIs & Services -> Library -> enable **Google Drive API**.
2. OAuth consent screen: User type External, any app name, your email. Add your Google account under **Test users**.
   Add the scope `.../auth/drive.appdata`. (Testing mode is fine for personal use.)
3. Credentials -> Create credentials -> **OAuth client ID** -> Web application.
   Authorized JavaScript origins: your site origin, for example `https://<user>.github.io` (no path, no trailing slash).
4. Copy the Client ID into `window.SYNC_CFG` in `index.html`.
5. Open the app -> Settings -> Cloud sync -> Sign in with Google. Sign in first on the device with the most progress.

Notes: Google browser sign-in gives 1-hour access, so after a while the status shows "Google session expired";
tap Sync now to reconnect. Local progress is never lost in the meantime. In Testing mode Google also expires
the grant after 7 days, so you may be asked to sign in again; publishing the consent screen to "In production" removes that.
