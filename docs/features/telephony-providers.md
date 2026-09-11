# Telephony providers: Plivo and Vonage

Tone answers and places phone calls through per-organisation telephony channels. Twilio and Telnyx were the first two; this guide covers Plivo and Vonage, which follow the same three registries: a `TelephonyProvider` for the inbound media websocket (`core/services/transport/`), a `CallEngine` for outbound origination (`core/services/call_engines/`), and a `CallTerminator` for the runtime hang-up (`core/services/call_termination/`). Webhooks live in `core/api/telephony_routes.py`, credentials in the org's channel row, decrypted by `core/services/transport/telephony_credentials.py`.

`BASE_CALL_URL` must be the public base of the call service; every webhook below is relative to it.

## Plivo

### Channel

Integrations → Channels → Plivo, with the account `auth_id` and `auth_token` from the Plivo console. Readiness probes the account and reports missing or rejected credentials and low cash credits. The channel page lists the account's numbers through `GET /api/v1/channel/plivo_phone_numbers?channel_id=<id>`.

### Inbound

In the Plivo console create a Voice application whose answer URL is `{BASE_CALL_URL}/plivo/answer` (POST) and assign the number to it. The webhook answers with Plivo XML that streams the call, bidirectionally at 8 kHz μ-law, to the media websocket:

```xml
<Response>
  <Stream bidirectional="true" keepCallAlive="true" contentType="audio/x-mulaw;rate=8000">
    wss://call-host/ws?from=%2B1555...&amp;to=%2B1555...
  </Stream>
</Response>
```

The caller and called numbers travel on the websocket query string; the transport backfills them into the call data, and falls back to a live-call lookup on the Plivo API when they are absent. Plivo sends bare digits (`13474282218`), so both paths normalise them to E.164 (`+13474282218`) before the number-to-agent lookup, and outbound dials strip the plus again for the Plivo API. The agent is resolved by the called number as for every other provider.

### Outbound

Outbound calls and scheduled batches select the Plivo engine automatically when the from-number belongs to a Plivo channel, or explicitly with the trigger provider `plivo`. The engine calls `POST /v1/Account/{auth_id}/Call/` with `answer_url = {BASE_CALL_URL}/plivo/outbound?agent_id=...&direction=outbound&from=...&to=...` and, for scheduled calls, `hangup_url = {BASE_CALL_URL}/plivo/outbound-status?scheduled_call_id=...`. Plivo returns a `request_uuid`, which is stored as the provider call id; the status callback maps `RequestUUID`, `CallStatus` and `Duration` onto the shared scheduled-call state machine.

Hang-up uses `DELETE /Call/{uuid}/` for a live call and `DELETE /Request/{uuid}/` for one still ringing; the Pipecat serializer's own hang-up on `EndFrame` stays enabled as well, so the terminator usually finds the call already gone and confirms that through the call detail record: an answered record is `completed`, an unanswered one maps its `hangup_cause_name` onto `busy`, `no-answer`, `canceled` or `failed`.

## Vonage

### Channel

Integrations → Channels → Vonage. Create a Vonage application with Voice capability and paste its `application_id` and the downloaded private key (PEM) into the channel; those two sign the Voice API requests with an RS256 JWT. Add the account `api_key` and `api_secret` to list numbers and let readiness check the balance (`GET https://rest.nexmo.com/account/get-balance`). Numbers are listed through `GET /api/v1/channel/vonage_phone_numbers?channel_id=<id>`.

### Inbound

On the Vonage application set the answer URL to `{BASE_CALL_URL}/vonage/answer` (GET) and the event URL to `{BASE_CALL_URL}/vonage/events` (POST), then link the number to the application. The answer webhook returns an NCCO that connects the call to the media websocket at 16 kHz linear PCM:

```json
[{"action": "connect", "endpoint": [{"type": "websocket",
   "uri": "wss://call-host/ws?provider=vonage&call_id=<uuid>&from=...&to=...",
   "content-type": "audio/l16;rate=16000"}]}]
```

Vonage's first websocket message has no provider marker, so the `/ws` endpoint reads `provider=vonage` and `call_id` from the query string and pre-seeds the transport with the Vonage serializer instead of sniffing the stream. The call uuid on the query string is what the terminator hangs up. Vonage, like Plivo, sends bare-digit numbers, so the answer webhook and the event webhook normalise them to E.164 before the number-to-agent lookup, and dials strip the plus again for the Voice API.

### Outbound

The engine calls `POST https://api.nexmo.com/v1/calls` with the agent, direction and numbers on the answer URL and the scheduled call id on the event URL. Vonage returns the call `uuid`; event webhooks (`started`, `ringing`, `answered`, `completed`, `busy`, `unanswered`, `timeout`, `failed`, `rejected`, `cancelled`) map onto the scheduled-call state machine. Hang-up is `PUT /v1/calls/{uuid}` with `{"action": "hangup"}`; the Vonage serializer has no hang-up of its own, so the runtime terminator is the only hang-up path. Warm transfer to a phone number is available through the same endpoint with a `transfer` action.

## Adding a provider

Implement `TelephonyProvider` (serializer plus optional from/to resolution), `CallEngine` (origination, hang-up, status, answer document, and `answer_media_type` when the provider expects JSON rather than XML) and `CallTerminator`, register each in its package `__init__`, add a credential loader, a readiness probe entry, the channel fields on the frontend, and the webhook routes. Providers whose websocket cannot be sniffed set `provider=<slug>` on the media websocket URL; providers that cannot carry custom parameters put the agent id, direction and numbers on that URL's query string, which `/ws` reads for every provider.
