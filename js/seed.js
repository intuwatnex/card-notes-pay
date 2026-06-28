/* Sample/demo data for the public repo — contains NO real financial information.
   On first run the app loads this so the UI is explorable. Replace it with your
   own data in the app, or use Settings -> Import to load a JSON backup. */
window.SEED = {
 "cards": [
  { "name": "Bank A (1234)", "stmtDate": 17, "dueDate": 2 },
  { "name": "Bank B (5678)", "stmtDate": 12, "dueDate": 1 },
  { "name": "Bank C (9012)", "stmtDate": 25, "dueDate": 12 }
 ],
 "spending": [
  { "card": "Bank A (1234)", "month": "2026-04", "amount": 3500 },
  { "card": "Bank B (5678)", "month": "2026-04", "amount": 1200 },
  { "card": "Bank C (9012)", "month": "2026-04", "amount": 800 },
  { "card": "Bank A (1234)", "month": "2026-05", "amount": 4200 },
  { "card": "Bank B (5678)", "month": "2026-05", "amount": 1500 }
 ],
 "income": [
  { "month": "2026-04", "amount": 50000 },
  { "month": "2026-05", "amount": 50000 }
 ],
 "installments": [
  { "bank": "Bank A", "detail": "Sample item", "start": "2026-03-15", "amount": 12000, "perMonth": 2000, "paid": 2, "totalMonth": 6 }
 ]
};
