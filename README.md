# wins.

A simple daily accomplishment logger that runs on your phone as a web app. Log what you get done as you do it — no matter how small.

## What it does

- **Log wins instantly** — type what you just finished, tap +
- **Auto-categorise** — each entry is automatically tagged (work, health, home, creative, etc.)
- **Flag follow-ups** — add a `#` anywhere in your text to mark something that needs follow-up
- **React to entries** — long press any item to add ⭐ 😊 💪 🔥 ✅
- **Yesterday summary** — opens with an AI-written summary of the previous day, highlighting your starred items and pending follow-ups
- **Share your log** — tap Share, pick a date range, send via WhatsApp / email or copy to clipboard
- **Works offline** — once loaded, no internet needed to log entries

## How to use it

Open the app at your GitHub Pages URL and tap **Add to Home Screen** in your browser menu. It will appear as an icon on your home screen and open fullscreen like a native app.

All data is stored locally on your device.

## Tips

- `finished the report #` → logged + flagged for follow-up
- Long press any entry → pick a reaction emoji
- Tap **Share** → choose Today / Yesterday / Week / All time → send or copy

## Files

| File | Purpose |
|---|---|
| `index.html` | The entire app |
| `manifest.json` | Makes it installable as a PWA |
| `sw.js` | Service worker for offline support |
| `icons/` | Home screen icons |

## Updating the app

To make changes, edit `index.html` directly in GitHub (tap the pencil icon) and commit. GitHub Pages will update within a minute.

---

Built as a PWA — no app store, no install, no account needed.

## License

MIT License · Copyright (c) 2026 Eucalyptus Dari
