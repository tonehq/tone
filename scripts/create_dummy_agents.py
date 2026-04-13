"""
Create 10 agents with a dummy agent config (copied from existing config id 11560)
and assign a phone number to each on channel 31.
"""
import requests

BASE_URL = "http://localhost:8000/api/v1"
AUTH_TOKEN = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VyX2lkIjoyLCJlbWFpbCI6InRoaWxhay5ndW5hc2VrYXJhbkBwcm9kdWN0ZnVzaW9uLmNvIiwib3JnX2lkIjoiOTRkMjgxMzgtYjU0MC00Mzg5LThkYzgtOWIzYmFlZjMyYmQ5Iiwicm9sZSI6Im93bmVyIiwiaWF0IjoxNzc1NzM2OTg0LCJleHAiOjE3NzU4MjMzODR9.CceVHS1OVpChC8D8cspB22dNM_-RQCIn4ZZJQR2snfU"
CHANNEL_ID = 2

HEADERS = {
    "Authorization": f"Bearer {AUTH_TOKEN}",
    "Content-Type": "application/json",
}

# Dummy agent config template (fields copied from local agent_configs.id=11560)
DUMMY_CONFIG = {
    "llm_service_id": 128,
    "tts_service_id": 162,
    "stt_service_id": 147,
    "first_message": "Hello",
    "system_prompt": (
        "<p>You are a polite and professional hotel receptionist. When the caller "
        "calls, greet them warmly and introduce the hotel. Help the caller with "
        "room booking enquiries. Ask the following questions one by one, in a "
        "natural conversation: 1. Check-in date 2. Check-out date 3. Number of "
        "guests 4. Type of room needed (single, double, deluxe, etc.). If the "
        "caller asks about price, give a reasonable estimate and clearly say that "
        "final pricing will be confirmed by the hotel staff. If the caller wants "
        "to make a booking, collect their full name, phone number, and email "
        "address</p>"
    ),
    "end_call_message": "Bye",
    "status": "active",
    "llm_metadata": {"model": "gpt-4-turbo"},
    "tts_metadata": {"voice_id": "e07c00bc-4134-4eae-9ea4-1a55fb45746b"},
    "stt_metadata": {},
    "agent_metadata": {
        "custom_vocabulary": None,
        "filter_words": None,
        "realistic_filler_words": False,
        "language": "en",
        "voice_speed": 50,
        "patience_level": "low",
        "speech_recognition": "fast",
        "call_recording": False,
        "call_transcription": False,
    },
}

PHONE_NUMBERS = [
    "+16827328687",
    "+13186201704",
    "+17405204895",
    "+13186682645",
    "+13187133023",
    "+12183093029",
    "+16562614918",
    "+19894742667",
    "+15076506421",
    "+12763881949",
]


def create_agent(idx: int) -> int:
    payload = {
        "name": f"Dummy Agent {idx}",
        "description": f"Auto-generated dummy agent #{idx}",
        "agent_type": "INBOUND",
        "system_prompt": DUMMY_CONFIG["system_prompt"],
        "first_message": DUMMY_CONFIG["first_message"],
        "language": "en",
    }
    r = requests.post(f"{BASE_URL}/agent/upsert_agent", json=payload, headers=HEADERS)
    r.raise_for_status()
    data = r.json()
    return data["id"]


def assign_phone_number(agent_id: int, phone: str) -> None:
    payload = {
        "phone_number": phone,
        "phone_number_sid": f"PN_dummy_{agent_id}",
        "phone_number_auth_token": "dummy_auth_token",
        "provider": "twilio",
        "channel_id": CHANNEL_ID,
        "agent_id": agent_id,
    }
    r = requests.post(
        f"{BASE_URL}/agent_channel_phone_number/upsert_channel_phone_number",
        json=payload,
        headers=HEADERS,
    )
    r.raise_for_status()


def main() -> None:
    import json, os
    created = []
    for i, phone in enumerate(PHONE_NUMBERS, start=1):
        try:
            agent_id = create_agent(i)
            print(f"[{i}] Created agent id={agent_id}")

            assign_phone_number(agent_id, phone)
            print(f"[{i}] Assigned {phone} to agent {agent_id}")
            created.append({"agent_id": agent_id, "phone_number": phone})
        except requests.HTTPError as e:
            print(f"[{i}] FAILED: {e} | body={e.response.text}")

    out = os.path.join(os.path.dirname(__file__), "dummy_agent_ids.json")
    with open(out, "w") as f:
        json.dump(created, f, indent=2)
    print(f"Wrote {len(created)} agents to {out}")


if __name__ == "__main__":
    main()
