# 💳 Card Notes & Pay

A mobile **PWA** (installable web app) for tracking credit-card spending, paying via saved **scan-to-pay QR codes**, and managing **installment plans** that auto-update over time.

- **Free** — no backend, no paid services.
- **On-device database** — data is stored in the browser's IndexedDB on *your* phone (private, works offline).
- **Hosted free on GitHub Pages.**
- **Bilingual** — Thai / English (toggle in the header).

Built from the structure of `installment plan as of jan 2021.xlsx` (sheets **Paid (CARD)** and **Installment**), and pre-seeded with that data on first run.

---

## Features

| Screen | What it does |
|--------|--------------|
| **สรุป / Home** | Monthly income, spending, amount-to-pay, installment load; upcoming due dates; per-card breakdown bars. Tap the income card to edit it. |
| **จ่าย / Pay** | Per card: amount, statement day, due day. Show the card's **QR code** to scan & pay, and mark as paid. |
| **บันทึก / Add** | Record spending per card per month with a note. |
| **ผ่อน / Installments** | Each plan shows per-month, paid/left months, remaining, last-payment date. Pick months (3–36), interest rate (0% or more) — **remaining months update automatically** as time passes. |
| **บัตร / Cards** | Add/edit cards: name/bank, statement day, due day, and upload a **PromptPay QR image**. |
| **⚙ Settings** | Language, **Excel (.xlsx) export**, **JSON backup/import**, reload sample data, wipe. |

### How installments auto-update
`per-month = (amount × (1 + interest%/100)) / months`. Paid months are derived from the start date vs. today (first payment on the start date), so **left months & remaining shrink automatically** every month. You can override "paid" manually if needed.

### QR codes (scan to pay)
Each card can hold its own payment QR (PromptPay or any bank QR). You can attach one in two places:
- On the **Pay** screen, a card with no QR shows **⬆ Upload QR** — tap it to pick a photo/screenshot (or take one with the camera).
- On the **Cards** screen, edit a card to upload / change / remove its QR.

Once a card has a QR, it is shown **inline on the Pay screen by default** so you can scan it straight away — tap it to enlarge full-screen (the popup also has **Change QR** / **Remove QR**). Images are downscaled and stored on-device.

---

## Run locally

No build step. Any static server works:

```bash
cd "CreditCard_Notes&Pay"
python3 -m http.server 4173
# open http://localhost:4173
```

> A service worker is used for offline support, so use `http://localhost` (not `file://`).

---

## Deploy free on GitHub Pages

1. Create a repo and push these files (the app must be at the repo root, or adjust paths):

   ```bash
   cd "CreditCard_Notes&Pay"
   git init
   git add .
   git commit -m "Card Notes & Pay PWA"
   git branch -M main
   git remote add origin https://github.com/<you>/<repo>.git
   git push -u origin main
   ```

2. On GitHub: **Settings → Pages → Build and deployment → Source: Deploy from a branch → Branch: `main` / root → Save.**

3. Wait ~1 min, then open `https://<you>.github.io/<repo>/` on your phone.

4. **Install it:** in mobile Safari/Chrome → Share/menu → **Add to Home Screen**. It now launches like a native app, full-screen and offline.

> All relative paths (`./...`) are used so it works under the `/<repo>/` subpath.

---

## Backup & export

- Your real spending data is **never** sent anywhere — it lives only in your phone's browser storage.
- **Settings → Export Excel (.xlsx)** downloads a real Excel file to your device with 4 sheets — `Paid (CARD)` (month × card matrix, like the original), `Installment` (with live-computed remaining), `Spending` (flat list), and `Cards`. Opens in Excel / Numbers / Google Sheets. This is a *read-only snapshot* — it cannot be re-imported.
- **Settings → Backup (.json)** saves a file you *can* re-import to restore everything (cards, QR images, spending, installments). Keep it safe — it is **not** meant to be committed publicly (`.gitignore` excludes `*backup*.json`).
- Restore on a new device with **Settings → Import (.json)**.
- Clearing browser data / uninstalling removes the on-device database, so keep exports.

---

## Tech

Vanilla JS · IndexedDB · Service Worker · Web App Manifest. No dependencies, no tracking.

## Project layout

```
index.html              app shell + tab bar
manifest.webmanifest    PWA metadata
sw.js                   service worker (network-first, offline fallback)
css/styles.css          mobile-first styling (dark/light auto)
js/i18n.js              Thai/English strings
js/db.js                IndexedDB wrapper
js/xlsx.js              dependency-free .xlsx writer (real Excel export)
js/app.js               screens, modals, installment math, backup
js/seed.js              initial data extracted from your Excel
icons/                  app icons
```
