from dataclasses import dataclass, field
from typing import Any, Dict, List


@dataclass
class ToolFixture:
    name: str
    server: str
    prompt: str
    expected_tool: str
    expected_params: Dict[str, Any] = field(default_factory=dict)
    threshold: float = 1.0
    system_prompt: str = (
        "You are a CRM assistant on a voice call. Use the available tools to act. "
        "You are pre-authorized; never ask the user to confirm before calling a tool."
    )
    tags: List[str] = field(default_factory=list)


FIXTURES: List[ToolFixture] = [
    ToolFixture(
        name="zoho_create_contact",
        server="zoho_crm_mcp",
        prompt=(
            "Please add me to Zoho CRM as a contact. "
            "My first name is Tone, my last name is Test, my email is tone.test@example.com."
        ),
        expected_tool="ZohoCRM_createRecords",
        expected_params={
            "path_variables": {"module": "Contacts"},
            "body": {"data": [{"First_Name": "Tone", "Last_Name": "Test",
                               "Email": "tone.test@example.com"}]},
        },
        threshold=0.5,
        tags=["write", "zoho"],
    ),
    ToolFixture(
        name="zoho_create_note",
        server="zoho_crm_mcp",
        prompt=(
            "Add a note to the Zoho Contacts record with id 1396225000000540001 "
            "titled 'Booking' saying the customer called about a booking."
        ),
        expected_tool="ZohoCRM_createNotes",
        expected_params={
            "path_variables": {"parentRecordModule": "Contacts",
                               "parentRecordId": "1396225000000540001"},
            "body": {"data": [{"Note_Title": "Booking",
                               "Note_Content": "The customer called about a booking."}]},
        },
        threshold=0.5,
        tags=["write", "zoho"],
    ),
    ToolFixture(
        name="zoho_search_contact",
        server="zoho_crm_mcp",
        prompt="Search Zoho Contacts for anyone called Tone.",
        expected_tool="ZohoCRM_searchRecords",
        expected_params={"path_variables": {"module": "Contacts"}},
        threshold=0.4,
        tags=["read", "zoho"],
    ),
    ToolFixture(
        name="salesforce_create_contact",
        server="salesforce_mcp",
        prompt="Add me to Salesforce as a new contact. My last name is Test.",
        expected_tool="createSobjectRecord",
        expected_params={"sobject-name": "Contact", "body": {"LastName": "Test"}},
        threshold=0.5,
        tags=["write", "salesforce"],
    ),
    ToolFixture(
        name="salesforce_who_am_i",
        server="salesforce_mcp",
        prompt="Which Salesforce org and user are you connected as?",
        expected_tool="getUserInfo",
        tags=["read", "salesforce"],
    ),
    ToolFixture(
        name="hubspot_user_details",
        server="hubspot_mcp",
        prompt="Which HubSpot account are you connected to?",
        expected_tool="get_user_details",
        expected_params={"include": ["USER_INFORMATION"]},
        threshold=0.4,
        tags=["read", "hubspot"],
    ),
]
