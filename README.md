# english-trainer

Business English Trainer, offline-first PWA.

- `/` main app (formerly v2): vocabulary from the Google Sheet `vocabulary_v2`, phrases from the published phrases sheet
- `/v1/` archived first version, kept for reference
- `/v2/` redirects to `/`

Progress is stored per browser: main app under `bet3.*`, v1 under `bet.*`.

## Cloud sync (Supabase + Google sign-in)

Progress (cards, daily log, bullet records) syncs between devices after you sign in with Google.
The app stays local-first: it works offline and syncs in the background. Merge rules: newer review wins per card,
daily counters and best scores take the max, "Erase all progress" is propagated via a `wipedAt` marker.
Sync settings are in Settings -> Cloud sync. Sources, theme and other settings are not synced.

One-time setup:

1. Create a project at supabase.com (free tier).
2. SQL Editor -> paste and run `supabase/schema.sql` (creates the `progress` table, row-level security, and hourly history snapshots).
3. Google Cloud Console -> APIs & Services -> Credentials -> OAuth client ID (type: Web application).
   Authorized redirect URI: `https://<project-ref>.supabase.co/auth/v1/callback`. Copy the client ID and secret.
4. Supabase -> Authentication -> Providers -> Google: enable it, paste the client ID and secret.
5. Supabase -> Authentication -> URL Configuration: Site URL = your GitHub Pages URL (for example `https://<user>.github.io/english-trainer/`),
   and add the same URL under Redirect URLs.
6. Supabase -> Project Settings -> API: copy the Project URL and the `anon` public key into `window.SYNC_CFG` in `index.html`.
   The anon key is public by design; access is protected by row-level security.
7. Open the app -> Settings -> Cloud sync -> Sign in with Google. On the first sign-in, existing local progress is merged into the cloud.

Tip: on the device with the most progress, sign in first, then sign in on the others.
Supabase free projects pause after about a week without activity; the first request after that wakes them from the dashboard.
