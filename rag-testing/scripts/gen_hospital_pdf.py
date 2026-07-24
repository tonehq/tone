"""One-off: generate a synthetic hospital knowledge-base PDF suitable for RAG
smoke tests. The content is varied — hard facts (numbers, hours, phone),
policy prose, lists, and edge-case rules — so the LLM question generator can
produce factual / negative / ambiguous / out-of-scope / edge questions.

Usage:
    python rag-testing/scripts/gen_hospital_pdf.py
    python rag-testing/scripts/gen_hospital_pdf.py --out /tmp/silvermeadow.pdf
"""
from __future__ import annotations

import argparse
from pathlib import Path

from reportlab.lib.enums import TA_JUSTIFY
from reportlab.lib.pagesizes import LETTER
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import (
    ListFlowable,
    ListItem,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)
from reportlab.lib import colors


HOSPITAL_NAME = "Silvermeadow General Hospital"


def _styles():
    ss = getSampleStyleSheet()
    ss.add(ParagraphStyle("Body", parent=ss["BodyText"], fontSize=10.5,
                          leading=14, alignment=TA_JUSTIFY, spaceAfter=6))
    ss.add(ParagraphStyle("H1", parent=ss["Heading1"], fontSize=18,
                          leading=22, spaceBefore=6, spaceAfter=10))
    ss.add(ParagraphStyle("H2", parent=ss["Heading2"], fontSize=13,
                          leading=17, spaceBefore=10, spaceAfter=6))
    return ss


def _para(text, s):
    return Paragraph(text, s["Body"])


def _h1(text, s):
    return Paragraph(text, s["H1"])


def _h2(text, s):
    return Paragraph(text, s["H2"])


def _bullets(items, s):
    return ListFlowable(
        [ListItem(_para(t, s), leftIndent=12) for t in items],
        bulletType="bullet",
        leftIndent=18,
    )


def _table(rows, col_widths=None):
    t = Table(rows, colWidths=col_widths, hAlign="LEFT")
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#3d5a80")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 9.5),
        ("BOTTOMPADDING", (0, 0), (-1, 0), 6),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.grey),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
    ]))
    return t


def build(story, s):
    story += [
        _h1(f"{HOSPITAL_NAME} — Patient Handbook & Operational Guide", s),
        _para(
            f"{HOSPITAL_NAME} is a 342-bed regional teaching hospital located at "
            "1487 Cedar Ridge Boulevard, Milbourne, OR 97402. The hospital was "
            "founded in 1963 by Dr. Ellinor Vasquez and has been continuously "
            "accredited by the Joint Commission since 1971. Silvermeadow serves "
            "approximately 118,000 emergency-department visits and 21,400 "
            "inpatient admissions each year across a 47-mile catchment.",
            s,
        ),
        _para(
            "This document is the definitive reference for patients, visitors, "
            "and referring clinicians. It supersedes all prior printed handbooks "
            "dated before January 2026.",
            s,
        ),

        _h2("1. Contact & Access", s),
        _table([
            ["Purpose", "Number / Address"],
            ["Main switchboard", "+1 (503) 555-0184"],
            ["Emergency department (24/7)", "+1 (503) 555-0100 (or dial 911)"],
            ["Appointments — outpatient clinics", "+1 (503) 555-0142"],
            ["Billing & financial counseling", "+1 (503) 555-0176 (Mon–Fri, 08:00–17:00 PT)"],
            ["Medical records requests", "records@silvermeadowgh.org"],
            ["Patient advocate hotline", "+1 (503) 555-0119 (24/7)"],
            ["Media & press inquiries", "press@silvermeadowgh.org"],
        ], col_widths=[2.4 * inch, 3.5 * inch]),
        Spacer(1, 6),
        _para(
            "The hospital campus has three public entrances. The Main Lobby "
            "(Cedar Ridge Blvd) is open 05:30–22:00 daily. The Emergency "
            "Department entrance on Juniper Lane is open continuously. The "
            "Oncology & Infusion entrance on Building C is open Monday through "
            "Saturday, 06:30–19:30, and is closed on Sundays.",
            s,
        ),

        _h2("2. Emergency Services", s),
        _para(
            "The Silvermeadow Emergency Department is a Level II trauma center "
            "verified by the American College of Surgeons since 2004. Average "
            "door-to-provider time in Q4 2025 was 11 minutes. Patients presenting "
            "with chest pain suggestive of ST-elevation myocardial infarction are "
            "brought to the cardiac catheterization lab within a mean of 47 "
            "minutes (door-to-balloon).",
            s,
        ),
        _para(
            "The ED uses a five-level Emergency Severity Index (ESI). Level 1 "
            "(immediate life threat) is seen without delay. Level 5 (minor "
            "complaint, no resources) may be redirected to the on-site Express "
            "Care clinic when open.",
            s,
        ),
        _para(
            "<b>Express Care</b> is a walk-in clinic located adjacent to the ED, "
            "open 09:00–21:00 seven days a week. It treats non-emergent "
            "conditions (sprains, minor lacerations, uncomplicated UTIs, "
            "flu-like illness) at a fixed self-pay rate of $189 per visit.",
            s,
        ),

        _h2("3. Visiting Hours & Rules", s),
        _bullets([
            "General medical/surgical floors: 09:00–20:30 daily. Two visitors per patient at a time.",
            "Intensive Care Unit (ICU): 10:00–13:00 and 16:00–19:00. One visitor at a time, must be 14 years or older.",
            "Neonatal ICU: Parents 24/7. Grandparents may visit 11:00–18:00 with a parent present.",
            "Behavioral Health Unit: 15:00–17:00 weekdays; 12:00–17:00 weekends. Visitors must be pre-registered.",
            "Oncology infusion suites: One support person permitted; no children under 12 due to infection risk.",
        ], s),
        _para(
            "All visitors must check in at the security desk, present a "
            "government-issued ID, and wear the printed wristband at all times "
            "while inside the building. During active respiratory-virus advisories, "
            "the hospital may restrict visits to one designated support person per "
            "patient for the duration of the advisory.",
            s,
        ),

        PageBreak(),

        _h2("4. Clinical Departments", s),
        _para(
            "Silvermeadow operates 27 clinical departments. The following list "
            "reflects the department directory as of January 15, 2026.",
            s,
        ),
        _table([
            ["Department", "Location (Bldg / Floor)", "Direct line"],
            ["Cardiology", "A / 4", "+1 (503) 555-0210"],
            ["Cardiothoracic Surgery", "A / 5", "+1 (503) 555-0215"],
            ["Dermatology", "C / 2", "+1 (503) 555-0221"],
            ["Endocrinology & Diabetes Center", "B / 3", "+1 (503) 555-0230"],
            ["Gastroenterology", "A / 3", "+1 (503) 555-0240"],
            ["General Surgery", "A / 2", "+1 (503) 555-0248"],
            ["Neurology", "B / 4", "+1 (503) 555-0255"],
            ["Obstetrics & Gynecology", "D / 2", "+1 (503) 555-0260"],
            ["Oncology (Medical)", "C / 3", "+1 (503) 555-0270"],
            ["Orthopedic Surgery", "A / 6", "+1 (503) 555-0281"],
            ["Pediatrics (inpatient)", "D / 4", "+1 (503) 555-0290"],
            ["Radiology & Imaging", "B / 1", "+1 (503) 555-0301"],
            ["Rehabilitation Medicine", "E / 1", "+1 (503) 555-0311"],
            ["Urology", "A / 3", "+1 (503) 555-0325"],
        ], col_widths=[2.6 * inch, 2.0 * inch, 1.6 * inch]),
        Spacer(1, 6),
        _para(
            "<b>Note:</b> The Cardiothoracic Surgery service does not accept "
            "self-referrals. All new patient consultations must be routed through "
            "a Cardiology attending or a primary care physician. Silvermeadow "
            "does <b>not</b> offer transplant services; patients requiring solid-organ "
            "transplant are referred to Portland Medical Center under our "
            "long-standing partnership agreement (renewed May 2024).",
            s,
        ),

        _h2("5. Admissions & Registration", s),
        _para(
            "Scheduled admissions are processed at the Admissions Desk in the "
            "Main Lobby between 06:00 and 18:00. Patients should arrive at least "
            "90 minutes before their scheduled procedure. Bring photo ID, "
            "insurance cards, a current medication list, and any advance "
            "directive documents.",
            s,
        ),
        _para(
            "Same-day surgery patients must have a designated adult driver present "
            "at discharge. Ride-share services are permitted only if the patient "
            "was not administered general anesthesia and is discharged by an RN "
            "who documents the exception in the chart.",
            s,
        ),

        _h2("6. Insurance & Billing", s),
        _para(
            "Silvermeadow is in-network with the following major carriers as of "
            "January 2026: Blue Cross Blue Shield of Oregon, Aetna, Cigna, "
            "United Healthcare (commercial and Medicare Advantage), Kaiser "
            "Permanente (emergency only), Regence, and TRICARE. Silvermeadow is "
            "<b>not</b> currently in-network with Ambetter or Oscar Health.",
            s,
        ),
        _para(
            "Medicaid patients on the Oregon Health Plan (OHP) are accepted for "
            "all inpatient and emergency services. Certain outpatient specialty "
            "services (specifically bariatric surgery evaluations and elective "
            "orthopedic joint replacement) require pre-authorization through the "
            "OHP coordinated-care organization.",
            s,
        ),
        _para(
            "Uninsured patients may qualify for the Silvermeadow Financial "
            "Assistance Program. Households at or below 200% of the federal "
            "poverty level receive a 100% discount on medically necessary care. "
            "Households between 201% and 400% receive a sliding-scale discount "
            "ranging from 75% to 25%. Applications must be submitted within 240 "
            "days of the first billing statement.",
            s,
        ),

        PageBreak(),

        _h2("7. Pharmacy Services", s),
        _para(
            "The Silvermeadow Outpatient Pharmacy is located on the ground floor "
            "of Building B and is open Monday through Friday 08:00–19:00, "
            "Saturday 09:00–14:00. The pharmacy is closed on Sundays and on "
            "federal holidays. A 24-hour medication vending kiosk in the ED "
            "lobby dispenses a limited formulary of post-discharge starter packs "
            "(most commonly prescribed antibiotics, analgesics, and inhalers).",
            s,
        ),
        _para(
            "Controlled substances (Schedule II) cannot be dispensed by the "
            "vending kiosk under any circumstance. Patients requiring such "
            "medications after pharmacy hours must arrange fulfillment through a "
            "24-hour community pharmacy; the ED provider will send an electronic "
            "prescription accordingly.",
            s,
        ),

        _h2("8. Advance Directives & Patient Rights", s),
        _para(
            "Every patient at Silvermeadow has the right to accept or refuse any "
            "treatment. Advance directives (living will, POLST, durable power of "
            "attorney for healthcare) are honored provided they are executed in "
            "accordance with Oregon Revised Statutes Chapter 127. Copies should "
            "be uploaded through the patient portal or brought to the admissions "
            "desk at check-in.",
            s,
        ),
        _para(
            "Patients have the right to a language interpreter at no cost. "
            "Silvermeadow contracts with a video-remote interpretation service "
            "covering more than 200 languages including American Sign Language, "
            "available on-demand from any inpatient room within 90 seconds.",
            s,
        ),

        _h2("9. Infection Control & Isolation Precautions", s),
        _bullets([
            "Standard precautions apply to every patient encounter (hand hygiene, appropriate PPE).",
            "Contact precautions are used for patients with MRSA, VRE, C. difficile, and multi-drug resistant organisms.",
            "Droplet precautions are used for influenza, pertussis, and meningococcal disease.",
            "Airborne isolation is required for tuberculosis, measles, and varicella; the hospital has 14 negative-pressure rooms (four in the ED, six in the ICU, four on the medical floor).",
            "Neutropenic precautions apply to patients with an absolute neutrophil count below 500/µL.",
        ], s),

        _h2("10. Cafeteria & Dining", s),
        _para(
            "The Silvermeadow Bistro on the ground floor of Building A is open "
            "06:30–20:00 daily. Room-service dining is available to inpatients "
            "on general floors from 06:45 to 19:15; orders placed after 18:45 "
            "are limited to the late menu. Patients on cardiac, renal, "
            "diabetic, or clear-liquid dietary orders receive automatically "
            "filtered menus. Guest trays for family members are $8.75 and can "
            "be ordered by the patient's nurse.",
            s,
        ),

        _h2("11. Parking & Transportation", s),
        _para(
            "The main parking garage is located on the corner of Cedar Ridge "
            "and Juniper. The first 30 minutes are free. Rates thereafter are "
            "$3 per hour, capped at $16 per day. Weekly passes ($55) and "
            "monthly passes ($185) are available at the security desk. Valet "
            "parking is offered at the Main Lobby entrance Monday through "
            "Friday, 07:30–18:00, at a flat rate of $12.",
            s,
        ),
        _para(
            "The city bus (routes 14 and 22) stops at the Cedar Ridge & 15th "
            "Ave. shelter directly in front of the Main Lobby. Wheelchair-"
            "accessible ride-share pickup is designated in Zone C of the "
            "parking garage.",
            s,
        ),

        PageBreak(),

        _h2("12. Frequently Asked Questions", s),
        _para(
            "<b>Q. Does Silvermeadow deliver babies?</b> Yes. The Family Birth "
            "Center on Building D, floor 2 has 18 labor-delivery-recovery "
            "rooms and a Level III NICU. Water births are supported in four "
            "designated rooms; a signed consent and a low-risk pregnancy "
            "determination by the delivering provider are required.",
            s,
        ),
        _para(
            "<b>Q. Are pets allowed?</b> Only certified service animals as "
            "defined by the Americans with Disabilities Act. Emotional-support "
            "animals are not permitted in patient care areas. The volunteer "
            "Pet Therapy program brings vetted therapy dogs to the general "
            "floors on Tuesdays and Thursdays between 14:00 and 16:00.",
            s,
        ),
        _para(
            "<b>Q. Can I smoke on hospital grounds?</b> No. The entire "
            "Silvermeadow campus, including parking garages and outdoor "
            "walkways, has been tobacco-free since March 1, 2018. This "
            "restriction extends to vaping and cannabis products regardless of "
            "state legalization status.",
            s,
        ),
        _para(
            "<b>Q. How do I request my medical records?</b> Email "
            "records@silvermeadowgh.org from the address on file, or submit an "
            "authorization form in person at the Health Information Management "
            "office (Building A, floor 1, room 118). Standard requests are "
            "fulfilled within 15 business days; expedited requests (for active "
            "clinical care) within 3 business days at no charge.",
            s,
        ),

        _h2("13. Key Personnel", s),
        _table([
            ["Role", "Name", "Since"],
            ["Chief Executive Officer", "Dr. Priya Ranganathan, MD, MBA", "2021"],
            ["Chief Medical Officer", "Dr. Marcus Halloway, MD", "2019"],
            ["Chief Nursing Officer", "Elena Boychuk, RN, DNP", "2023"],
            ["Chief Financial Officer", "Terrence Okafor, CPA", "2020"],
            ["ED Medical Director", "Dr. Jia-Lin Xu, MD, FACEP", "2022"],
            ["Chair, Ethics Committee", "Rev. Nomvula Sithole, DMin", "2024"],
            ["Director of Patient Safety", "Marisol Delacroix, MHA, CPPS", "2022"],
        ], col_widths=[2.5 * inch, 2.4 * inch, 0.9 * inch]),

        _h2("14. Quality & Outcome Metrics (2025 Annual)", s),
        _bullets([
            "30-day all-cause readmission rate: 12.4% (national benchmark 15.3%).",
            "Central-line-associated bloodstream infections (CLABSI) per 1,000 line-days: 0.71.",
            "Hospital-acquired pressure injury rate (stage 2+): 0.9 per 1,000 patient-days.",
            "Patient satisfaction (HCAHPS top-box overall rating): 78%.",
            "Time-to-antibiotic for severe sepsis (median): 42 minutes.",
        ], s),
        _para(
            "Silvermeadow General Hospital does <b>not</b> publicly report "
            "surgeon-level outcome data at this time; patients seeking such "
            "figures may request them through the Patient Advocate office.",
            s,
        ),

        _h2("15. Document Control", s),
        _para(
            "Version 8.2. Approved by the Silvermeadow Board of Directors on "
            "January 15, 2026. Next scheduled review: July 15, 2026. Questions "
            "or corrections should be routed to the Compliance Office "
            "(compliance@silvermeadowgh.org).",
            s,
        ),
    ]


def main() -> int:
    ap = argparse.ArgumentParser(description="Generate a synthetic hospital PDF for RAG testing.")
    ap.add_argument(
        "--out",
        default=str(Path(__file__).resolve().parents[1] / "silvermeadow_general_hospital.pdf"),
        help="Output PDF path (default: rag-testing/silvermeadow_general_hospital.pdf)",
    )
    args = ap.parse_args()

    out_path = Path(args.out).expanduser().resolve()
    out_path.parent.mkdir(parents=True, exist_ok=True)

    s = _styles()
    doc = SimpleDocTemplate(
        str(out_path),
        pagesize=LETTER,
        title=f"{HOSPITAL_NAME} — Patient Handbook",
        author="Silvermeadow General Hospital",
        leftMargin=0.9 * inch,
        rightMargin=0.9 * inch,
        topMargin=0.9 * inch,
        bottomMargin=0.9 * inch,
    )
    story: list = []
    build(story, s)
    doc.build(story)
    print(f"[gen_hospital_pdf] wrote {out_path} ({out_path.stat().st_size / 1024:.1f} KB)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
