"""Generate a sample hotel booking document PDF for testing the document tool."""

from fpdf import FPDF


def generate():
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)

    # --- Page 1: Hotel Overview & Room Types ---
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 22)
    pdf.cell(0, 12, "The Grand Horizon Hotel", new_x="LMARGIN", new_y="NEXT", align="C")
    pdf.set_font("Helvetica", "", 11)
    pdf.cell(0, 7, "123 Ocean Drive, Miami Beach, FL 33139", new_x="LMARGIN", new_y="NEXT", align="C")
    pdf.cell(0, 7, "Phone: +1 (305) 555-0199  |  Email: reservations@grandhorizon.com", new_x="LMARGIN", new_y="NEXT", align="C")
    pdf.cell(0, 7, "Website: www.grandhorizon.com", new_x="LMARGIN", new_y="NEXT", align="C")
    pdf.ln(8)

    pdf.set_font("Helvetica", "B", 14)
    pdf.cell(0, 10, "Room Types & Rates (2026 Season)", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 10)

    rooms = [
        ("Standard Room", "$149/night", "1 Queen bed, city view, 280 sq ft, free Wi-Fi, mini fridge"),
        ("Deluxe Room", "$219/night", "1 King bed, partial ocean view, 350 sq ft, free Wi-Fi, mini bar, coffee maker"),
        ("Ocean Suite", "$389/night", "1 King bed + living area, full ocean view, 520 sq ft, balcony, mini bar, Nespresso machine"),
        ("Presidential Suite", "$749/night", "2 King beds, panoramic ocean view, 980 sq ft, private terrace, jacuzzi, butler service"),
        ("Family Room", "$269/night", "2 Queen beds, garden view, 400 sq ft, free Wi-Fi, mini fridge, kid-friendly amenities"),
    ]

    for name, rate, desc in rooms:
        pdf.set_font("Helvetica", "B", 11)
        pdf.cell(60, 7, name)
        pdf.set_font("Helvetica", "B", 11)
        pdf.cell(40, 7, rate)
        pdf.set_font("Helvetica", "", 10)
        pdf.multi_cell(0, 7, desc)
        pdf.ln(2)

    pdf.ln(5)
    pdf.set_font("Helvetica", "B", 14)
    pdf.cell(0, 10, "Seasonal Pricing", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 10)
    pdf.multi_cell(0, 6,
        "- Peak Season (Dec 15 - Apr 15): Rates as listed above.\n"
        "- Shoulder Season (Apr 16 - Jun 14, Oct 1 - Dec 14): 20% discount on all room types.\n"
        "- Off-Peak Season (Jun 15 - Sep 30): 35% discount on all room types.\n"
        "- Holiday surcharge (Christmas, New Year, July 4th): +$50/night on all rooms.\n"
        "- Weekly stay discount: Book 7+ nights and get 10% off the total.\n"
        "- Early bird: Book 60+ days in advance for an additional 5% off."
    )

    pdf.ln(5)
    pdf.set_font("Helvetica", "B", 14)
    pdf.cell(0, 10, "Check-in / Check-out Policy", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 10)
    pdf.multi_cell(0, 6,
        "- Standard check-in: 3:00 PM  |  Check-out: 11:00 AM\n"
        "- Early check-in (subject to availability): $35 fee, available from 12:00 PM\n"
        "- Late check-out (subject to availability): $35 fee, extends to 2:00 PM\n"
        "- Express check-out available via the in-room TV or mobile app.\n"
        "- Government-issued photo ID and credit card required at check-in.\n"
        "- Minimum age for check-in: 21 years."
    )

    # --- Page 2: Amenities, Dining & Policies ---
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 14)
    pdf.cell(0, 10, "Hotel Amenities", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 10)
    pdf.multi_cell(0, 6,
        "- Infinity pool (heated, open 7 AM - 10 PM)\n"
        "- Private beach access with complimentary towels and umbrellas\n"
        "- Fitness center (24/7 access, Peloton bikes, free weights)\n"
        "- Horizon Spa: massages from $120, facials from $95 (book at front desk or ext. 401)\n"
        "- Business center with printing and meeting rooms (free for guests)\n"
        "- Complimentary airport shuttle (runs every 2 hours, 6 AM - 10 PM)\n"
        "- Valet parking: $28/day  |  Self-parking: $18/day\n"
        "- EV charging stations: 4 Tesla Superchargers, 2 universal Level 2 chargers (free)\n"
        "- Concierge desk available 24/7 for tours, restaurant reservations, and tickets\n"
        "- Kids' club (ages 4-12): complimentary, open 9 AM - 5 PM daily"
    )

    pdf.ln(5)
    pdf.set_font("Helvetica", "B", 14)
    pdf.cell(0, 10, "Dining Options", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 10)

    dining = [
        ("The Coral Restaurant", "Breakfast 6:30-10:30 AM, Dinner 6-10 PM. Seafood & international cuisine, smart casual dress code."),
        ("Sunset Bar & Grill", "11 AM - 11 PM. Poolside casual dining, burgers, salads, cocktails."),
        ("Lobby Lounge", "4 PM - midnight. Craft cocktails, wine, light bites, live jazz on Fri/Sat."),
        ("In-Room Dining", "24 hours. Full menu available, $8 delivery fee, 18% gratuity auto-added."),
    ]

    for name, desc in dining:
        pdf.set_font("Helvetica", "B", 10)
        pdf.cell(0, 6, name, new_x="LMARGIN", new_y="NEXT")
        pdf.set_font("Helvetica", "", 10)
        pdf.multi_cell(0, 6, desc)
        pdf.ln(2)

    pdf.ln(5)
    pdf.set_font("Helvetica", "B", 14)
    pdf.cell(0, 10, "Cancellation & Refund Policy", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 10)
    pdf.multi_cell(0, 6,
        "- Free cancellation up to 72 hours before check-in date.\n"
        "- Cancellation within 72-24 hours: 1 night's charge.\n"
        "- Cancellation within 24 hours or no-show: full stay charged.\n"
        "- Refunds processed within 5-10 business days to original payment method.\n"
        "- Group bookings (5+ rooms): separate cancellation policy applies, contact sales.\n"
        "- Non-refundable rate: available at 15% discount, no cancellations or changes allowed."
    )

    pdf.ln(5)
    pdf.set_font("Helvetica", "B", 14)
    pdf.cell(0, 10, "Pet Policy", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 10)
    pdf.multi_cell(0, 6,
        "- Dogs and cats welcome (max 2 pets per room, under 50 lbs each).\n"
        "- Pet fee: $45/night per pet.\n"
        "- Pet-friendly rooms: Standard and Deluxe rooms only.\n"
        "- Pets must be leashed in common areas. Pet relief area located near the garden.\n"
        "- Complimentary pet bed and water bowl provided upon request."
    )

    pdf.ln(5)
    pdf.set_font("Helvetica", "B", 14)
    pdf.cell(0, 10, "Loyalty Program - Horizon Rewards", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 10)
    pdf.multi_cell(0, 6,
        "- Silver (0-9 nights/year): Earn 5 points per $1 spent, free Wi-Fi.\n"
        "- Gold (10-24 nights/year): Earn 8 points per $1, free breakfast, room upgrade (subject to availability).\n"
        "- Platinum (25+ nights/year): Earn 12 points per $1, free breakfast, guaranteed upgrade, late check-out, lounge access.\n"
        "- Points redemption: 10,000 points = 1 free night (Standard), 15,000 = Deluxe, 25,000 = Ocean Suite.\n"
        "- Points expire after 24 months of inactivity."
    )

    # --- Page 3: FAQs ---
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 14)
    pdf.cell(0, 10, "Frequently Asked Questions", new_x="LMARGIN", new_y="NEXT")

    faqs = [
        ("What is the closest airport?", "Miami International Airport (MIA), approximately 20 minutes by car. Our complimentary shuttle runs every 2 hours."),
        ("Is breakfast included?", "Breakfast is included for Gold and Platinum Horizon Rewards members. For other guests, buffet breakfast at The Coral Restaurant is $32/adult, $16/child (under 12)."),
        ("Do you offer airport transfers?", "Yes. Complimentary shared shuttle every 2 hours (6 AM-10 PM). Private car service available for $65 one-way (book 24 hours in advance)."),
        ("Can I request a specific room or floor?", "Room and floor preferences can be noted during booking but are not guaranteed. We do our best to accommodate all requests."),
        ("Is there a resort fee?", "Yes, a daily resort fee of $35 applies. It covers pool/beach access, fitness center, Wi-Fi, and local calls."),
        ("Do you accommodate special dietary needs?", "Absolutely. Our restaurants cater to vegetarian, vegan, gluten-free, and kosher diets. Please inform us 24 hours in advance for kosher meals."),
        ("What is the smoking policy?", "The hotel is 100% non-smoking indoors. Designated smoking areas are available on the ground floor terrace."),
        ("Do you have accessible rooms?", "Yes, ADA-compliant rooms are available in all room categories. Please request at time of booking."),
        ("Can I host an event or wedding?", "Yes! We have 3 event spaces (capacity 20-300 guests). Contact events@grandhorizon.com or call ext. 502 for packages starting at $5,000."),
        ("What payment methods are accepted?", "Visa, Mastercard, Amex, Discover, Apple Pay, Google Pay. Cash deposits accepted at front desk for incidentals."),
    ]

    for q, a in faqs:
        pdf.set_font("Helvetica", "B", 10)
        pdf.cell(0, 6, f"Q: {q}", new_x="LMARGIN", new_y="NEXT")
        pdf.set_font("Helvetica", "", 10)
        pdf.multi_cell(0, 6, f"A: {a}")
        pdf.ln(3)

    output_path = "/Users/thilak/Documents/Tone/dev/grand_horizon_hotel_info.pdf"
    pdf.output(output_path)
    print(f"PDF generated: {output_path}")


if __name__ == "__main__":
    generate()
