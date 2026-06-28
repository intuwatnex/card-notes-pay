#!/bin/bash
# One-command monthly sync: fetch statements from Gmail -> parse -> build import file.
# Your birthdate is only used in-memory to derive PDF passwords; it is never stored.
set -e
cd "$(dirname "$0")"

echo "==> Fetching statement emails from Gmail..."
python3 fetch_statements.py

if [ -z "$CARDPAY_DOB" ]; then
  read -p "Enter your birthdate (DD/MM/YYYY) to unlock the PDFs: " CARDPAY_DOB
fi

echo "==> Parsing PDFs and building import file..."
CARDPAY_DOB="$CARDPAY_DOB" python3 parse_statements.py

echo
echo "Done. Import file: ~/Downloads/cardpay-mydata.json"
echo "Open the app -> Settings -> Import (.json) -> pick that file."
