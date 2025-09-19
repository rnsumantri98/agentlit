import streamlit as st
import re, io, json, hashlib, requests, datetime as dt
from dataclasses import dataclass, asdict
from typing import List, Optional, Dict, Any

# ---------- Utilities: file parsing ----------
def read_txt(file_bytes: bytes) -> str:
    try:
        return file_bytes.decode("utf-8", errors="ignore")
    except Exception:
        return file_bytes.decode("latin-1", errors="ignore")

def read_pdf(file_bytes: bytes) -> str:
    # lightweight, no external web: PyPDF2
    import PyPDF2
    text = []
    with io.BytesIO(file_bytes) as f:
        reader = PyPDF2.PdfReader(f)
        for page in reader.pages:
            text.append(page.extract_text() or "")
    return "\n".join(text)

def read_docx(file_bytes: bytes) -> str:
    import docx
    with io.BytesIO(file_bytes) as f:
        doc = docx.Document(f)
    return "\n".join([p.text for p in doc.paragraphs])

def load_text(uploaded) -> str:
    name = uploaded.name.lower()
    data = uploaded.read()
    if name.endswith(".pdf"):
        return read_pdf(data)
    elif name.endswith(".docx"):
        return read_docx(data)
    elif name.endswith(".txt"):
        return read_txt(data)
    else:
        # try best-effort text decode
        return read_txt(data)

# ---------- Heuristics: extraction ----------
DATE_PAT = re.compile(
    r"(?P<date>(?:\d{1,2}\s?(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec)[a-z]*\s?,?\s?\d{2,4})|(?:\d{4}-\d{2}-\d{2})|(?:\d{1,2}[/-]\d{1,2}[/-]\d{2,4}))",
    re.IGNORECASE,
)

def normalize_date(s: str) -> Optional[str]:
    s = s.strip().replace(",", " ")
    for fmt in ("%Y-%m-%d", "%d-%m-%Y", "%d/%m/%Y", "%m/%d/%Y", "%d %b %Y", "%d %B %Y", "%b %d %Y", "%B %d %Y"):
        try:
            return dt.datetime.strptime(s, fmt).date().isoformat()
        except Exception:
            pass
    # try flexible
    try:
        from dateutil import parser
        return parser.parse(s, dayfirst=True, fuzzy=True).date().isoformat()
    except Exception:
        return None

def find_first_date_near(text: str, anchors: List[str]) -> Optional[str]:
    low = text.lower()
    for a in anchors:
        idx = low.find(a.lower())
        if idx != -1:
            window = text[max(0, idx-120): idx+200]
            m = DATE_PAT.search(window)
            if m:
                d = normalize_date(m.group("date"))
                if d:
                    return d
    # fallback: any date in document
    m = DATE_PAT.search(text)
    if m:
        d = normalize_date(m.group("date"))
        return d
    return None

def capture_between(text: str, label: str, stop_labels: List[str], max_len=600) -> Optional[str]:
    """Grab a short span after 'label' until next stop label or max_len."""
    low = text.lower()
    i = low.find(label.lower())
    if i == -1:
        return None
    seg = text[i+len(label): i+len(label)+max_len]
    end = len(seg)
    for s in stop_labels:
        j = seg.lower().find(s.lower())
        if j != -1:
            end = min(end, j)
    return seg[:end].strip().strip(":").strip()

def extract_parties(text: str) -> Optional[str]:
    # heuristic around "between", "by and between", "parties", "party"
    patterns = [
        r"between\s+(.*?)\s+and\s+(.*?)[\.;\n]",
        r"by and between\s+(.*?)\s+and\s+(.*?)[\.;\n]",
        r"the parties:\s*(.*?)\n",
    ]
    for p in patterns:
        m = re.search(p, text, re.IGNORECASE | re.DOTALL)
        if m:
            parties = " & ".join([re.sub(r'\s+', ' ', g).strip(' ,.;') for g in m.groups()])
            return parties[:400]
    # fallback: capture after "Parties"
    cap = capture_between(text, "Parties", ["Governing Law", "Services", "Scope", "\n\n", "\n-"])
    return cap[:400] if cap else None

def extract_title(text: str, filename: str) -> Optional[str]:
    # Prefer explicit labels; else from first lines or filename
    labels = ["Contract Title", "Title", "Agreement Title", "This Agreement", "Services Agreement", "Amendment"]
    for lb in labels:
        cap = capture_between(text, lb, ["\n", "Date", "Parties", "Between"])
        if cap and len(cap) >= 3:
            return cap[:200]
    # first non-empty line
    for line in text.splitlines()[:10]:
        s = line.strip()
        if len(s) > 5 and len(s) < 160:
            return s
    # filename fallback
    return filename.rsplit(".", 1)[0]

def extract_services(text: str) -> Optional[str]:
    cap = capture_between(text, "Services", ["Payment", "Fees", "Charges", "Term", "Termination", "Governing", "\n\n"])
    if cap: return re.sub(r'\s+', ' ', cap)[:500]
    for kw in ["Scope of Work", "Scope", "Statement of Work"]:
        cap = capture_between(text, kw, ["Payment", "Fees", "Charges", "Term", "Termination", "Governing", "\n\n"])
        if cap: return re.sub(r'\s+', ' ', cap)[:500]
    return None

def extract_payment(text: str) -> Optional[str]:
    for kw in ["Payment Terms", "Fees", "Charges", "Compensation", "Pricing"]:
        cap = capture_between(text, kw, ["Term", "Termination", "Service", "Scope", "Governing", "\n\n"])
        if cap: return re.sub(r'\s+', ' ', cap)[:500]
    return None

def extract_termination(text: str) -> Optional[str]:
    for kw in ["Termination", "Term and Termination", "Right to Terminate"]:
        cap = capture_between(text, kw, ["Governing", "Confidential", "Fees", "Payment", "\n\n"])
        if cap: return re.sub(r'\s+', ' ', cap)[:700]
    return None

def extract_gov_law(text: str) -> Optional[str]:
    for kw in ["Governing Law", "Applicable Law", "Law and Jurisdiction"]:
        cap = capture_between(text, kw, ["Jurisdiction", "Dispute", "Venue", "Arbitration", "\n\n"])
        if cap: return re.sub(r'\s+', ' ', cap)[:200]
    m = re.search(r"governed by the laws? of ([A-Za-z ,.&()-]+)", text, re.IGNORECASE)
    if m:
        return m.group(1).strip()[:200]
    return None

def find_end_date(text: str) -> Optional[str]:
    # prioritise "End Date", "Expiry", "Term ends", else any date near "Term"
    labels = ["End Date", "Expiry Date", "Expiration Date", "Term ends", "end of term", "termination date"]
    d = find_first_date_near(text, labels)
    if d: return d
    return find_first_date_near(text, ["Term", "Duration"])

def find_contract_date(text: str) -> Optional[str]:
    return find_first_date_near(text, ["Contract Date", "Effective Date", "Date of Agreement", "Dated"])

# ---------- Risk detection (rule-based, ISO 31000-ish) ----------
RISK_PATTERNS = {
    "Unlimited liability": r"unlimited liability|liability.*(without|no)\s+limit",
    "Auto-renewal > 1 year": r"auto-?renew(al)?|automatic renewal|renew.*automatically",
    "One-sided termination": r"termination.*(at will|sole discretion|without cause).*(by (?:only )?one party|by (?:the )?company|by (?:the )?supplier)",
    "Broad indemnity": r"indemnif(y|ication).*(any|all).*claims",
    "IP ownership ambiguous": r"intellectual property|IP.*(remain|transfer|assign)",
    "Confidentiality missing": r"confidentiality",
    "Data protection missing": r"(gdpr|ccpa|data protection|personal data|privacy)",
    "Jurisdiction far": r"exclusive jurisdiction|venue.*(foreign|outside)",
    "Penalties/Liquidated damages": r"liquidated damages|penalt(y|ies)",
    "No SLA/Service levels": r"service level|SLA"
}

@dataclass
class RiskFinding:
    name: str
    present: bool
    details: Optional[str] = None
    severity: str = "Medium"  # Low/Medium/High

def detect_risks(text: str, governing_law: Optional[str]) -> List[RiskFinding]:
    low = text.lower()
    findings: List[RiskFinding] = []
    def snippet(pat):
        m = re.search(pat, text, re.IGNORECASE | re.DOTALL)
        if not m: return None
        s = text[max(0, m.start()-80): m.end()+80]
        return re.sub(r'\s+', ' ', s)[:240]

    # core detections
    for name, pat in RISK_PATTERNS.items():
        found = re.search(pat, low, re.IGNORECASE) is not None
        sev = "Medium"
        if name in ["Unlimited liability", "Broad indemnity", "One-sided termination"]:
            sev = "High"
        details = snippet(pat) if found else None
        # Missing clauses (confidentiality/data protection) invert logic
        if name in ["Confidentiality missing", "Data protection missing"]:
            # If pattern not found, it's missing -> present=True finding
            present = not found
            details = "Clause appears missing in document." if present else snippet(pat)
            sev = "High" if present and name == "Data protection missing" else sev
            findings.append(RiskFinding(name=name, present=present, details=details, severity=sev))
        else:
            findings.append(RiskFinding(name=name, present=bool(found), details=details, severity=sev))

    # Jurisdiction heuristic (if gov law exists and seems far—very rough)
    if governing_law:
        if re.search(r"indonesia|republic of indonesia|id", governing_law, re.IGNORECASE):
            # lower risk for local jurisdiction
            for f in findings:
                if f.name == "Jurisdiction far" and f.present:
                    f.severity = "Low"
    return findings

def compute_risk_score(findings: List[RiskFinding]) -> Dict[str, Any]:
    weights = {"Low": 1, "Medium": 2, "High": 3}
    total = 0
    count = 0
    for f in findings:
        if f.present:
            total += weights[f.severity]
            count += 1
    score = total
    rating = "Low"
    if score >= 6 and score < 12: rating = "Medium"
    if score >= 12: rating = "High"
    return {"score": score, "rating": rating, "issues_found": count}

# ---------- Sanitization for transport ----------
def short_hash(s: str) -> str:
    return hashlib.sha1(s.encode("utf-8")).hexdigest()[:10]

def truncate(s: Optional[str], n=700) -> Optional[str]:
    if not s: return s
    return s if len(s) <= n else s[:n] + " ..."

def telegram_safe(s: str) -> str:
    # remove characters that sometimes break markdown/HTML parsers
    return re.sub(r"[*_`<>]", "", s)

# ---------- Streamlit UI ----------
st.set_page_config(page_title="Contract Reviewer", page_icon="📄", layout="wide")
st.title("📄 Contract Reviewer — Upload & Review & Send to n8n")

with st.sidebar:
    st.header("Settings")
    webhook_url = st.text_input("n8n Webhook URL (POST JSON)", placeholder="https://n8n.example/webhook/contract_review")
    contract_owner = st.text_input("Your Organization / Owner (optional)")
    assumed_locale = st.selectbox("Date Locale Parsing", ["day-first (DD/MM/YYYY)", "month-first (MM/DD/YYYY)"], index=0)
    st.caption("Tips: simpan URL webhook n8n Anda di sini, lalu klik **Kirim ke n8n** setelah review.")

uploaded = st.file_uploader("Unggah kontrak (PDF, DOCX, TXT)", type=["pdf", "docx", "txt"])

if uploaded:
    raw_text = load_text(uploaded)
    if not raw_text or len(raw_text.strip()) < 20:
        st.error("Gagal membaca teks dari dokumen. Pastikan file tidak terenkripsi atau coba format lain.")
        st.stop()

    with st.expander("🔎 Teks ekstrak (preview)", expanded=False):
        st.text_area("Teks", raw_text[:20000], height=220)

    # Extraction
    title = extract_title(raw_text, uploaded.name)
    parties = extract_parties(raw_text)
    contract_date = find_contract_date(raw_text)
    end_date = find_end_date(raw_text)
    services = extract_services(raw_text)
    payment = extract_payment(raw_text)
    termination = extract_termination(raw_text)
    governing_law = extract_gov_law(raw_text)

    # Days left
    days_left = None
    if end_date:
        try:
            d_end = dt.date.fromisoformat(end_date)
            days_left = (d_end - dt.date.today()).days
        except Exception:
            days_left = None

    # Risk analysis
    findings = detect_risks(raw_text, governing_law)
    risk_meta = compute_risk_score(findings)

    # Summary panel
    st.subheader("🧭 Executive Summary")
    col1, col2, col3 = st.columns([1.2,1,1])
    with col1:
        st.write(f"**Contract Title:** {title or '-'}")
        st.write(f"**Parties:** {parties or '-'}")
        st.write(f"**Governing Law:** {governing_law or '-'}")
    with col2:
        st.write(f"**Contract Date:** {contract_date or '-'}")
        st.write(f"**End Date:** {end_date or '-'}")
        st.write(f"**Days Left:** {days_left if days_left is not None else '-'}")
    with col3:
        st.metric("Risk Score", risk_meta["score"], delta=None)
        st.write(f"**Risk Rating:** {risk_meta['rating']}")
        st.write(f"**Issues Found:** {risk_meta['issues_found']}")

    st.divider()

    # Key sections
    st.subheader("📑 Key Clauses (Extracted)")
    st.markdown(f"**Services**\n\n{services or '_Not found_'}")
    st.markdown(f"**Payment Terms**\n\n{payment or '_Not found_'}")
    st.markdown(f"**Termination**\n\n{termination or '_Not found_'}")

    # Findings
    st.subheader("🚩 Risk Findings (Rule-based)")
    sever_map = {"High":"🔴 High", "Medium":"🟠 Medium", "Low":"🟡 Low"}
    for f in findings:
        if f.present:
            with st.expander(f"{sever_map.get(f.severity, f.severity)} — {f.name}", expanded=False):
                st.write(truncate(f.details or "Detected.", 1000))

    # ISO 31000-ish recommendation block
    st.subheader("🛡️ Recommendations (ISO 31000-aligned)")
    recs = []
    if any(f.present and f.name=="Unlimited liability" for f in findings):
        recs.append("Tambahkan **liability cap** (mis. 100% dari fee 12 bulan terakhir) dan eksklusi kerugian tidak langsung.")
    if any(f.present and f.name=="Broad indemnity" for f in findings):
        recs.append("Persempit **indemnity** menjadi pelanggaran hukum, IP infringement, dan kelalaian berat; pastikan mutual jika relevan.")
    if any(f.present and f.name=="One-sided termination" for f in findings):
        recs.append("Pastikan **termination for convenience** bersifat **mutual** atau kompensasi wajar bila sepihak.")
    if any(f.present and f.name=="Data protection missing" for f in findings):
        recs.append("Tambahkan **Data Processing/Addendum** (peran, dasar hukum, transfer data lintas negara, keamanan, breach notice).")
    if any(f.present and f.name=="Confidentiality missing" for f in findings):
        recs.append("Masukkan klausul **Confidentiality/NDA** yang jelas (cakupan, durasi pasca-terminasi, pengecualian).")
    if governing_law and not re.search(r"indonesia|republic of indonesia", governing_law, re.IGNORECASE):
        recs.append("Tinjau **governing law & venue** agar sejalan dengan kepentingan perusahaan (biaya litigasi & enforceability).")
    if not recs:
        recs.append("Tidak ada temuan kritikal berbasis rule; tetap lakukan review legal final sebelum penandatanganan.")
    st.markdown("- " + "\n- ".join(recs))

    # Payload to send
    review_payload = {
        "meta": {
            "file_name": uploaded.name,
            "file_id": short_hash(uploaded.name + str(len(raw_text))),
            "generated_at": dt.datetime.utcnow().isoformat() + "Z",
            "owner": contract_owner or None
        },
        "summary": {
            "contract_title": title,
            "parties": parties,
            "contract_date": contract_date,
            "end_date": end_date,
            "days_left": days_left,
            "governing_law": governing_law,
            "risk_score": risk_meta["score"],
            "risk_rating": risk_meta["rating"],
            "issues_found": risk_meta["issues_found"],
        },
        "clauses": {
            "services": services,
            "payment_terms": payment,
            "termination": termination
        },
        "risks": [
            {
                "name": f.name,
                "severity": f.severity,
                "details": truncate(f.details, 500)
            } for f in findings if f.present
        ],
        "raw": {
            "text_excerpt": truncate(raw_text, 3000)
        }
    }

    st.divider()
    st.subheader("📤 Kirim Review ke n8n")
    st.code(json.dumps(review_payload, indent=2, ensure_ascii=False)[:2000] + ("..." if len(json.dumps(review_payload))>2000 else ""), language="json")
    colA, colB = st.columns([1,1])

    with colA:
        if st.button("Kirim ke n8n (POST JSON)", use_container_width=True, type="primary", disabled=not webhook_url):
            try:
                resp = requests.post(webhook_url, json=review_payload, timeout=20)
                if 200 <= resp.status_code < 300:
                    st.success(f"Berhasil dikirim ke n8n (status {resp.status_code}).")
                    st.caption(f"Response: {resp.text[:400]}")
                else:
                    st.error(f"Gagal kirim (status {resp.status_code}). Cek webhook n8n Anda.")
                    st.caption(f"Response: {resp.text[:400]}")
            except Exception as e:
                st.error(f"Error koneksi: {e}")

    with colB:
        st.download_button(
            "Unduh JSON Review",
            data=json.dumps(review_payload, ensure_ascii=False, indent=2),
            file_name=f"contract_review_{short_hash(uploaded.name)}.json",
            mime="application/json",
            use_container_width=True
        )

else:
    st.info("Unggah file kontrak untuk memulai analisis (PDF/DOCX/TXT).")
