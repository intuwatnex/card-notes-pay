# Cardpay Gmail Sync

Reads your credit-card e-statement emails from Gmail, unlocks the password-protected
PDFs, extracts each card's **Total Payment Due** per month, and writes an import file
for the **Card Notes & Pay** app. Runs entirely on your Mac — nothing is uploaded.

## One-time setup
See **SETUP.md** (create a Google OAuth credential, save `credentials.json` here,
`pip3 install -r requirements.txt`).

## Best: one-tap Sync from inside the app
Start the local sync server (keep it running while you use the app):
```
python3 sync_server.py
```
It prints two URLs — open the app from one of them:
- on this Mac: `http://localhost:8787`
- on your phone (same Wi-Fi): `http://<your-mac-ip>:8787`

Then just tap **🔄 Sync** in the app — it reads Gmail, parses the latest
statements, and refreshes the data automatically (no file picking). Your
birthdate (for the PDF passwords) lives in `config.json` on this Mac.

> The public GitHub Pages app can't reach the local server (browsers block
> https→http), so use these URLs for one-tap sync. The Pages app still works
> with manual file import.

## Or: command-line (produces a file to import)
```
./sync.sh
```
It will:
1. fetch statement emails from the card issuers (KBANK, CardX/SCB, ttb, KTC, Krungsri, Central The 1),
2. ask your birthdate (used only in memory to derive the PDF passwords — never stored),
3. write **`~/Downloads/cardpay-mydata.json`**.

Then in the app: **⚙ Settings → Import (.json)** → pick that file.

Run the steps manually if you prefer:
```
python3 fetch_statements.py                 # downloads PDFs to ./statements/
CARDPAY_DOB=DD/MM/YYYY python3 parse_statements.py   # -> ~/Downloads/cardpay-mydata.json
```

## How passwords work
Every issuer locks the PDF with your birthdate in its own format. They are all derived
from one date (`CARDPAY_DOB`):

| Issuer | Format | Example (23 May 1996) |
|---|---|---|
| KTC | ddMmmyy | `23May96` |
| KBANK, CardX/SCB | DDMMYYYY | `23051996` |
| ttb, Krungsri, Central The 1 | ddMmmyyyy | `23May1996` |

## Notes / limits
- The app stores **Total Payment Due** per card per month (what you owe that statement).
- Krungsri / Central The 1 may only appear when you request a statement copy (they don't
  always email monthly e-statements to this address).
- Non-card mail (mutual funds, savings accounts, brokerage, installment receipts, NCB
  letters) is automatically skipped.
- `import` **replaces** the app's data with this file. Edits you make in the app
  (notes, QR images) are not preserved across a re-import — re-import is for refreshing
  the statement numbers.

## Security
- `.gitignore` blocks `credentials.json`, `token.json`, `statements/`, and `*.json`
  from being committed. This folder is **not** part of the public app repo.
- Gmail scope is **read-only**. Token can be revoked anytime at
  https://myaccount.google.com/permissions
