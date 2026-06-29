#!/bin/bash
# Double-click to make the sync server start automatically at login (runs in the
# background — no Terminal window). Re-run after moving this folder.
set -e
cd "$(dirname "$0")"
DIR="$(pwd)"
PY="$(command -v python3)"
PLIST="$HOME/Library/LaunchAgents/com.cardpay.sync.plist"
mkdir -p "$HOME/Library/LaunchAgents"

cat > "$PLIST" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key><string>com.cardpay.sync</string>
  <key>ProgramArguments</key>
  <array>
    <string>$PY</string>
    <string>$DIR/sync_server.py</string>
  </array>
  <key>WorkingDirectory</key><string>$DIR</string>
  <key>RunAtLoad</key><true/>
  <key>KeepAlive</key><true/>
  <key>StandardOutPath</key><string>/tmp/cardpay-sync.log</string>
  <key>StandardErrorPath</key><string>/tmp/cardpay-sync.err</string>
</dict>
</plist>
EOF

launchctl unload "$PLIST" 2>/dev/null || true
launchctl load "$PLIST"
echo "✓ Auto-start enabled. The sync server now runs at login (port from config.json)."
echo "  Logs: /tmp/cardpay-sync.log"
echo
echo "To turn OFF auto-start:"
echo "  launchctl unload \"$PLIST\" && rm \"$PLIST\""
echo
read -p "Press Return to close."
