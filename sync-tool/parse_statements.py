#!/usr/bin/env python3
"""
Parse decrypted e-statement PDFs -> per card: monthly "Total Payment Due",
individual transactions, and installment plans. Builds cardpay-mydata.json
in the app's import format.

Passwords are DERIVED from your birthdate (env CARDPAY_DOB=DD/MM/YYYY); the
date itself is never stored.

Usage:  CARDPAY_DOB=23/05/1996 python3 parse_statements.py
"""
import os, re, json, glob, sys
from pathlib import Path
from datetime import datetime
from pypdf import PdfReader

HERE = Path(__file__).resolve().parent
PDFS = HERE / "statements"
EMAILS = PDFS / "_emails.json"

MONTHS = {m: i for i, m in enumerate(
    ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"], 1)}
THMON = {"ม.ค":1,"ก.พ":2,"มี.ค":3,"เม.ย":4,"พ.ค":5,"มิ.ย":6,
         "ก.ค":7,"ส.ค":8,"ก.ย":9,"ต.ค":10,"พ.ย":11,"ธ.ค":12}


def derive_passwords(dob):
    d = datetime.strptime(dob, "%d/%m/%Y")
    dd, mmm, yyyy = f"{d.day:02d}", d.strftime("%b"), f"{d.year}"
    return {"ktc": f"{dd}{mmm}{yyyy[2:]}", "kbank": f"{dd}{d.month:02d}{yyyy}",
            "cardx": f"{dd}{d.month:02d}{yyyy}", "ttb": f"{dd}{mmm}{yyyy}",
            "krungsri": f"{dd}{mmm}{yyyy}", "central": f"{dd}{mmm}{yyyy}"}


def clean(t): return (t or "").replace("ำา", "ำ")
def num(s): return round(float(s.replace(",", "")), 2)


def read_pdf(path, pw):
    r = PdfReader(str(path))
    if r.is_encrypted and str(r.decrypt(pw)) == "PasswordType.NOT_DECRYPTED":
        return None
    return clean("\n".join((p.extract_text() or "") for p in r.pages))


def ym_from_filename(fn):
    fl = fn.lower()
    m = re.search(r"(20\d\d)(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)", fl)
    if m: return f"{m.group(1)}-{MONTHS[m.group(2).title()]:02d}"
    m = re.search(r"(\d{2})-(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)-(20\d\d)", fl)
    if m: return f"{m.group(3)}-{MONTHS[m.group(2).title()]:02d}"
    m = re.search(r"_(\d{2})(\d{2})(20\d\d)\b", fn)
    if m: return f"{m.group(3)}-{m.group(2)}"
    m = re.search(r"_(\d{2})(\d{2})(\d{2})\b", fn)
    if m: return f"20{m.group(1)}-{m.group(2)}"
    return None


def ym_from_date(s):
    """YYYY-MM from a dd/mm/yy or dd/mm/yyyy statement date."""
    m = re.search(r"\d{1,2}/(\d{2})/(\d{2,4})", s or "")
    if not m:
        return None
    yy = m.group(2)
    return f"{yy if len(yy) == 4 else '20' + yy}-{m.group(1)}"


def day(s):
    m = re.search(r"(\d{2})[/-]\d{2}[/-]\d{2,4}", s or "")
    return int(m.group(1)) if m else None


def mk_tx(date, desc, amount):
    desc = re.sub(r"\s+", " ", desc).strip()[:60]
    return {"date": date, "desc": desc, "amount": amount}


# ---------------- statement parsers (return list of card dicts) ----------------
TX_DDMMYY = re.compile(r"(\d{2}/\d{2}/\d{2})\s+\d{2}/\d{2}/\d{2}\s+(.+?)\s+(-?[\d,]+\.\d{2})\s*$", re.M)
TX_DDMMYYYY = re.compile(r"(\d{2}/\d{2}/\d{4})\s+\d{2}/\d{2}/\d{4}\s+(.+?)\s+(-?[\d,]+\.\d{2})\s*$", re.M)


def p_ktc(txt, fn):
    last4 = re.search(r"-(\d{4})\b", txt)
    last4 = last4.group(1) if last4 else "????"
    typ = re.search(r"TYPE OF CARD\s*:\s*(.+)", txt)
    typ = (typ.group(1).replace("CREDIT CARD", "").replace("CARD", "").strip().title()
           if typ else "KTC")
    close = re.search(r"วันสรุปยอดบัญชี\s*(\d{2}/\d{2}/\d{2})", txt)
    due = re.search(r"วันครบกำหนดชำระ\s*(\d{2}/\d{2}/\d{2})", txt)
    pay = re.search(r"ยอดที่ต้องชำระ/ชำระเกิน\D*?([\d,]+\.\d{2})", txt)
    tx = [mk_tx(d, ds, num(a)) for d, ds, a in TX_DDMMYY.findall(txt)
          if not re.search(r"x 16% x|365", ds)]
    return [dict(issuer="KTC", last4=last4, type=typ,
                 stmt=close.group(1) if close else "", due=due.group(1) if due else "",
                 amount=num(pay.group(1)) if pay else None, tx=tx)]


def p_kbank(txt, fn):
    stmt = re.search(r"STATEMENT DATE\s*(\d{2}/\d{2}/\d{4})", txt)
    due = re.search(r"DUE DATE\s*(\d{2}/\d{2}/\d{4})", txt)
    stmt = stmt.group(1) if stmt else ""; due = due.group(1) if due else ""
    bal = {}
    for m in re.finditer(r"(\d{4}) \d{2}XX XXXX (\d{4})\s+[A-Z.\s]+?\s+([\d,]+)\s+([\d,]+\.\d{2})\s+([\d,]+\.\d{2})", txt):
        bal[m.group(2)] = num(m.group(4))
    out = []
    for blk in re.split(r"/ ACCOUNT DETAILS", txt)[1:]:
        hm = re.match(r"\s+(.+?)\s+(\d{4}) \d{2}XX XXXX (\d{4})", blk)
        if not hm:
            continue
        typ, last4 = hm.group(1).strip().title(), hm.group(3)
        seg = re.split(r"TOTAL BALANCE", blk)[0]
        tx = [mk_tx(d, ds, num(a)) for d, ds, a in TX_DDMMYY.findall(seg)]
        out.append(dict(issuer="KBANK", last4=last4, type=typ, stmt=stmt, due=due,
                        amount=bal.get(last4), tx=tx))
    return out


def p_cardx(txt, fn):
    last4 = re.search(r"5414 96XX XXXX (\d{4})", txt) or re.search(r"XXXX (\d{4})", txt)
    bal = re.search(r"([\d,]+\.\d{2})TOTAL BALANCE", txt)
    due = re.search(r"(\d{2}/\d{2}/\d{2,4}).{0,30}PAYMENT DUE", txt, re.S)
    # concatenated dates: "<desc> THA20/1221/12 496.00"
    tx = []
    for m in re.finditer(r"(.+?)\s*(\d{2}/\d{2})(\d{2}/\d{2})\s+(-?[\d,]+\.\d{2})", txt):
        desc = m.group(1).strip()
        if len(desc) < 3 or "XXXX" in desc:
            continue
        tx.append(mk_tx(m.group(2), desc, num(m.group(4))))
    return [dict(issuer="CardX", last4=last4.group(1) if last4 else "1834", type="UP2ME",
                 stmt="", due=due.group(1) if due else "",
                 amount=num(bal.group(1)) if bal else None, tx=tx)]


def p_ttb(txt, fn):
    m = re.search(r"(\d{4})-\d{2}XX-XXXX-(\d{4})\s+(\d{2}/\d{2}/\d{4})\s+(\d{2}/\d{2}/\d{4})", txt)
    last4 = m.group(2) if m else "5788"
    stmt = m.group(3) if m else ""; due = m.group(4) if m else ""
    g = (re.search(r"GRAND TOTAL\s+([\d,]+\.\d{2})", txt)
         or re.search(r"SUB TOTAL BALANCE\s+([\d,]+\.\d{2})", txt))
    tx = [mk_tx(d, ds, num(a)) for d, ds, a in TX_DDMMYYYY.findall(txt)]
    return [dict(issuer="ttb", last4=last4, type="", stmt=stmt, due=due,
                 amount=num(g.group(1)) if g else None, tx=tx)]


def _krungsri_like(txt, brand):
    last4 = re.search(r"(\d{4}) \d{2}XX XXXX (\d{4})", txt)
    last4 = last4.group(2) if last4 else "????"
    pay = re.search(r"Total Payment Due For Credit Card\s+([\d,]+\.\d{2})", txt)
    tx = [mk_tx(d, ds, num(a)) for d, ds, a in TX_DDMMYY.findall(txt)
          if not re.search(r"x16%|/365", ds)]
    inst = None
    im = re.search(r"Installment Purchase\s+([\d,]+)\s*baht.*?=\s*([\d,]+)\s*baht/month", txt, re.S)
    if im:
        principal = num(im.group(1))
        perm = num(im.group(2))
        mm = re.search(r"for\s+(\d+)\s*months", txt)
        months = int(mm.group(1)) if mm else max(1, round(principal / perm)) if perm else 1
        rate = round((perm * months / principal - 1) * 100, 2) if principal else 0
        # installment period: a date-pair on one line >60 days apart (start … end)
        start = None
        for d1, d2 in re.findall(r"(\d{2}/\d{2}/\d{2})\s+(\d{2}/\d{2}/\d{2})", txt):
            try:
                a = datetime.strptime(d1, "%d/%m/%y"); b = datetime.strptime(d2, "%d/%m/%y")
                if (b - a).days > 60:
                    start = a.strftime("%Y-%m-%d"); break
            except ValueError:
                pass
        inst = dict(principal=principal, perMonth=perm, totalMonths=months,
                    interestRate=rate, startDate=start)
    # Krungsri/Central put no date in the filename, so read the statement's own
    # closing + due dates (the first two dd/mm/yy in the header) to date the record.
    hdr = re.findall(r"\b(\d{2}/\d{2}/\d{2})\b", txt)
    stmt = hdr[0] if hdr else ""
    due = hdr[1] if len(hdr) > 1 else ""
    return [dict(issuer="Krungsri", last4=last4, type=brand, stmt=stmt, due=due,
                 amount=num(pay.group(1)) if pay else None, tx=tx, inst=inst)]


def p_krungsri(txt, fn): return _krungsri_like(txt, "")
def p_central(txt, fn):  return _krungsri_like(txt, "Central The 1")


# ---------------- ttb installment receipt (car loan) ----------------
def parse_ttb_receipt(txt):
    detail = re.search(r"ประเภทสินค้า\s*:?\s*([^\n]+?)\s+เลข", txt)
    total = re.search(r"จำนวนงวด\s*:?\s*(\d+)\s*งวด", txt)
    nxt = re.search(r"ค่างวดถัดไป\s+(\d+)\(([^)]+)\)\s*จาก\s*(\d+)\s*งวด\s+([\d,]+\.\d{2})", txt)
    payday = re.search(r"ชำระทุกวันที่\s*:?\s*(\d+)", txt)
    if not (nxt and total):
        return None
    next_no = int(nxt.group(1))
    th = re.match(r"\s*(\d{1,2})?\(?([฀-๿.]+)/(\d{2})", nxt.group(2))
    # month/year of NEXT installment, e.g. "ก.พ/69"
    mm = re.search(r"([฀-๿.]+)/(\d{2})", nxt.group(2))
    perm = num(nxt.group(4))
    tot = int(total.group(1))
    pd = int(payday.group(1)) if payday else 11
    start = ""
    if mm and mm.group(1) in THMON:
        nm = THMON[mm.group(1)]; ny = 2500 + int(mm.group(2)) - 543
        # next installment date -> back out to installment #1
        base = datetime(ny, nm, min(pd, 28))
        month0 = base.month - 1 - (next_no - 1)
        y = base.year + month0 // 12
        mo = month0 % 12 + 1
        start = f"{y}-{mo:02d}-{pd:02d}"
    return dict(detail=(detail.group(1).strip() if detail else "ttb auto loan"),
                perMonth=perm, totalMonths=tot, startDate=start)


# ---------------- routing ----------------
SENDER = [("kasikornbank.com", p_kbank, "kbank"), ("cardx.co.th", p_cardx, "cardx"),
          ("ttbbank.com", p_ttb, "ttb"), ("ktc.co.th", p_ktc, "ktc"),
          ("krungsri.com", p_krungsri, "krungsri"), ("centralthe1card.com", p_central, "central")]
FNAME = [("ktc", p_ktc, "ktc"), ("k-email", p_kbank, "kbank"), ("kbgc", p_kbank, "kbank"),
         ("cardx_e-statement", p_cardx, "cardx"), ("ttb_e-credit", p_ttb, "ttb")]
SKIP = ("interest_calculation", "bualuang", "mutual_fund", "krungthai", "innovestx",
        "e-ncb", "cardx_support")


def route(fn, sender):
    fl = fn.lower()
    if "receipt_installment" in fl:
        return "ttb_receipt", "ttb"
    if any(s in fl for s in SKIP):
        return None, None
    s = (sender or "").lower()
    for dom, parser, pw in SENDER:
        if dom in s:
            return parser, pw
    for key, parser, pw in FNAME:
        if key in fl:
            return parser, pw
    return None, None


def email_month(h):
    m = re.search(r"(\d{1,2})\s+(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+(20\d\d)", h or "")
    return f"{m.group(3)}-{MONTHS[m.group(2)]:02d}" if m else None


def main():
    dob = os.environ.get("CARDPAY_DOB")
    if not dob:
        sys.exit("Set CARDPAY_DOB=DD/MM/YYYY")
    PW = derive_passwords(dob)
    att2date, att2from = {}, {}
    if EMAILS.exists():
        for r in json.load(open(EMAILS)):
            for a in r["attachments"]:
                att2date[a], att2from[a] = r["date"], r["from"]

    records, ttb_receipts, skipped = [], [], []
    for f in sorted(glob.glob(str(PDFS / "*.pdf")) + glob.glob(str(PDFS / "*.PDF"))):
        fn = os.path.basename(f)
        parser, pwkey = route(fn, att2from.get(fn, ""))
        if not parser:
            skipped.append(fn); continue
        txt = read_pdf(f, PW[pwkey])
        if txt is None:
            skipped.append(fn + " (decrypt failed)"); continue
        if parser == "ttb_receipt":
            r = parse_ttb_receipt(txt)
            if r: ttb_receipts.append(r)
            continue
        fallback = ym_from_filename(fn) or email_month(att2date.get(fn))
        for rec in parser(txt, fn):
            if rec["amount"] is None:
                skipped.append(fn + " (no amount)"); continue
            # Prefer the statement's own closing date (most accurate); else filename/email.
            rec["month"] = ym_from_date(rec.get("stmt")) or fallback
            rec["file"] = fn
            records.append(rec)

    # Dedup: one statement per (card, month) — the same statement can arrive twice
    # (e.g. a regular e-statement + a call-center copy). Keep the richer one.
    best = {}
    for r in records:
        k = (r["issuer"], r["last4"], r["month"])
        if k not in best or len(r["tx"]) > len(best[k]["tx"]):
            best[k] = r
    records = list(best.values())

    # ---- print verification ----
    records.sort(key=lambda r: (r["issuer"], r["last4"], r["month"] or ""))
    print(f"\n{'issuer':<10}{'last4':<7}{'month':<9}{'amount':>12}  #tx")
    print("-" * 48)
    for r in records:
        print(f"{r['issuer']:<10}{r['last4']:<7}{r['month'] or '?':<9}{r['amount']:>12,.2f}  {len(r['tx'])}")
    print(f"\n{len(records)} card-months, "
          f"{sum(len(r['tx']) for r in records)} transactions, "
          f"{len(ttb_receipts)} ttb-receipt(s)")

    build_import(records, ttb_receipts)
    if skipped:
        print("\nskipped:", len(skipped), "files (inserts / non-card / receipts handled separately)")


PALETTE = ["#6366f1","#ec4899","#14b8a6","#f59e0b","#ef4444","#8b5cf6","#06b6d4","#84cc16","#f97316","#3b82f6","#a855f7","#10b981"]

# Friendly nicknames per card (keyed by last 4 digits). Card name = "Nickname ••last4".
NICKNAMES = {
    "0742": "Shopee",        # KBANK Shopee
    "3915": "KBank Passion", # KBANK The Passion
    "5788": "ttb",
    "1834": "SCB",           # CardX (SCB)
    "5389": "KTC Visa",
    "8789": "KTC Master",
    "3317": "KTC JCB",
    "6287": "KTC UnionPay",
    "7338": "Krungsri",
    "1289": "Central The 1",
}


def build_import(records, ttb_receipts):
    PAID_THROUGH = "2026-05"
    cards, order = {}, []
    for r in records:
        key = (r["issuer"], r["last4"])
        if key not in cards:
            nick = NICKNAMES.get(r["last4"], r["issuer"])
            nm = f"{nick} ••{r['last4']}"
            cards[key] = dict(id=len(cards) + 1, name=nm, bank=r["issuer"],
                              stmtDate=day(r["stmt"]), dueDate=day(r["due"]),
                              qr=None, color=PALETTE[len(cards) % len(PALETTE)])
            order.append(key)
        else:
            c = cards[key]
            c["stmtDate"] = c["stmtDate"] or day(r["stmt"])
            c["dueDate"] = c["dueDate"] or day(r["due"])

    spending, transactions = [], []
    sid = tid = 1
    for r in records:
        cid = cards[(r["issuer"], r["last4"])]["id"]
        paid = bool(r["month"] and r["month"] <= PAID_THROUGH)
        spending.append(dict(id=sid, cardId=cid, month=r["month"], amount=r["amount"],
                             note="", paid=paid,
                             paidDate=f"{r['month']}-28T00:00:00.000Z" if paid else None))
        sid += 1
        for t in r["tx"]:
            transactions.append(dict(id=tid, cardId=cid, month=r["month"],
                                     date=t["date"], desc=t["desc"], amount=t["amount"]))
            tid += 1

    # ---- installments ----
    installments = []
    iid = 1
    # ttb car loan (use the receipt with the most progress / latest start)
    if ttb_receipts:
        best = sorted(ttb_receipts, key=lambda x: x.get("startDate") or "")[-1]
        installments.append(dict(id=iid, bank="ttb", detail=best["detail"],
                                 startDate=best["startDate"] or "2025-01-11",
                                 principal=round(best["perMonth"] * best["totalMonths"], 2),
                                 totalMonths=best["totalMonths"], interestRate=0,
                                 perMonth=best["perMonth"], manualPaid=None))
        iid += 1
    # Krungsri/Central installment lines from statements
    seen_inst = set()
    for r in records:
        ins = r.get("inst")
        if not ins:
            continue
        sig = (r["issuer"], r["last4"], ins["principal"], ins["perMonth"])
        if sig in seen_inst:
            continue
        seen_inst.add(sig)
        installments.append(dict(id=iid, bank=r["issuer"],
                                 detail=f"{r['type'] or r['issuer']} installment",
                                 startDate=ins.get("startDate") or f"{r['month']}-01",
                                 principal=ins["principal"], totalMonths=ins["totalMonths"],
                                 interestRate=ins["interestRate"], perMonth=ins["perMonth"],
                                 manualPaid=None))
        iid += 1

    out = dict(_app="CardNotesPay", _version=1, _exportedAt=datetime.utcnow().isoformat() + "Z",
               cards=[cards[k] for k in order], spending=spending,
               transactions=transactions, income=[], installments=installments,
               meta=[{"key": "seeded", "value": True}, {"key": "paidThrough2026-05", "value": True}])
    dest = Path(os.path.expanduser("~/Downloads/cardpay-mydata.json"))
    dest.write_text(json.dumps(out, ensure_ascii=False, indent=2))
    print(f"[ok] wrote {dest}")
    print(f"     {len(out['cards'])} cards, {len(spending)} card-months, "
          f"{len(transactions)} transactions, {len(installments)} installments")


if __name__ == "__main__":
    main()
