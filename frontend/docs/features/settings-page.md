# Settings Page - Feature Documentation

## Overview

The Settings page (`/settings`) is the centralized configuration hub for managing organization-level settings in Tone. It provides four sections accessible via a sidebar navigation: **API Keys**, **Members**, **Organization**, and **Web Hooks**.

**Route:** `/settings`
**Auth Required:** Yes (authenticated users only)
**Component:** `src/app/(dashboard)/settings/page.tsx`

---

## Page Layout

The Settings page uses a two-panel layout:

| Panel                          | Description                                                |
| ------------------------------ | ---------------------------------------------------------- |
| **Left Sidebar** (200px fixed) | Vertical navigation with icon+label items for each section |
| **Main Content** (flexible)    | Renders the active section's content                       |

**Sidebar Navigation Items:**

| Section      | Icon     | Path                     |
| ------------ | -------- | ------------------------ |
| API Key      | Key      | `/settings/api-key`      |
| Members      | User     | `/settings/members`      |
| Organization | Building | `/settings/organization` |
| Web Hook     | Network  | `/settings/web-hook`     |

**Component:** `src/components/settings/SidebarComponent.tsx`
**Config:** `src/components/settings/constants.tsx`

---

## 1. API Keys Section

The API Keys section manages authentication credentials for programmatic access to the Tone platform. It contains two tabs: **API Keys** and **Public Keys**.

**Component:** `src/components/settings/Apikeys.tsx`

### 1.1 API Keys Tab

Manages private API keys used for server-to-server authentication.

**Component:** `src/components/settings/ApiKeysTab.tsx`

#### Data Model

| Field       | Type              | Description                           |
| ----------- | ----------------- | ------------------------------------- |
| `id`        | string (UUID)     | Unique identifier                     |
| `name`      | string            | Human-readable key name               |
| `keyValue`  | string            | The API key value (masked by default) |
| `masked`    | boolean           | Whether the key is currently masked   |
| `createdAt` | string            | ISO timestamp of creation             |
| `tag`       | string (optional) | Optional label/tag for the key        |

#### Features

**1.1.1 List API Keys**

- Displays all API keys in a DataGrid table
- Columns: Name (with icon + optional tag), Key Value, Created At, Actions
- Keys are masked by default (displayed as `"..........."`
- Sortable and responsive column layout

**1.1.2 Create API Key**

- Trigger: "Add Key" button (top-right of table)
- Opens a modal dialog with:
  - **Key Name** (text input, required)
- Validation: Name must be non-empty (trimmed)
- On submit: Generates a UUID-based key, adds to list in masked state

**1.1.3 Row Actions (per key)**

- Accessed via three-dot menu icon on each row
- Available actions:
  - **Reveal Key** - Unmasks the key value for viewing
  - **Delete Key** - Removes the key

#### API Endpoints

| Method | Endpoint                            | Description                 | Auth                     |
| ------ | ----------------------------------- | --------------------------- | ------------------------ |
| GET    | `/api/v1/generated-api-keys/list`   | List all API keys           | `require_authenticated`  |
| POST   | `/api/v1/generated-api-keys/upsert` | Create or update an API key | `require_admin_or_owner` |
| DELETE | `/api/v1/generated-api-keys/delete` | Delete an API key           | `require_admin_or_owner` |

#### Integration Status

- Fetch on mount: Partial (calls list endpoint)
- Create: Local state only (backend not wired)
- Reveal: Local state only
- Delete: Local state only

---

### 1.2 Public Keys Tab

Manages client-side public keys with domain restrictions and security features.

**Component:** `src/components/settings/PublicKeysTab.tsx`

#### Data Model

| Field             | Type          | Description                                  |
| ----------------- | ------------- | -------------------------------------------- |
| `id`              | string (UUID) | Unique identifier                            |
| `name`            | string        | Human-readable key name                      |
| `keyValue`        | string        | The public key value                         |
| `domains`         | string        | Comma-separated allowed domains              |
| `abusePrevention` | boolean       | Google reCAPTCHA integration flag            |
| `fraudProtection` | boolean       | IP & destination number fraud detection flag |
| `createdAt`       | string        | ISO timestamp of creation                    |

#### Features

**1.2.1 List Public Keys**

- Displays all public keys in a DataGrid table
- Columns: Name, Key Value, Domains, Abuse Prevention (On/Off), Fraud Protection (On/Off), Created At, Actions
- Status toggles displayed as text labels ("On" / "Off")

**1.2.2 Create Public Key**

- Trigger: "Add Key" button (top-right of table)
- Opens a modal dialog with:
  - **Key Name** (text input, required)
  - **Allowed Domains** (multi-add input with chips)
    - Type a domain and click "Add" or press Enter
    - Domains display as removable chips
    - Duplicate domains are rejected
  - **Abuse Prevention** (toggle switch)
    - Description: Integrates Google reCAPTCHA for bot protection
    - Links to external documentation
  - **Fraud Protection** (toggle switch)
    - Description: Auto-detects suspicious requests by IP & destination number
- Validation: Key name must be non-empty

**1.2.3 Row Actions (per key)**

- Accessed via three-dot menu icon on each row
- Available actions:
  - **Reveal Key** - Unmasks the key value for viewing
  - **Delete Key** - Removes the key

#### Integration Status

- All operations are local state only (no backend wired)

---

## 2. Members Section

The Members section manages organization team members, their roles, and invitations.

**Rendered in:** `src/app/(dashboard)/settings/page.tsx` (inline)

### Features

**2.1 Search Members**

- Search bar at the top of the section
- Placeholder: "Search members..."
- Icon: Search (magnifying glass)
- Fixed width: 300px

**2.2 Invite User**

- Trigger: "Invite user" button with UserPlus icon
- Opens invite workflow (to be implemented)
- Expected fields:
  - Name (string, required)
  - Email (string, required)
  - Role (string, required - e.g., "admin", "member")

**2.3 Members List**

- Displays organization members in a vertical list
- Each member row shows:
  - **Avatar** - Circular avatar with initial letter
  - **Name** - Full name of the member
  - **Email** - Displayed below the name in secondary text
  - **Role** - Badge showing role (e.g., "Owner", "Admin", "Member")
  - **Delete** - Trash icon button (disabled for owner accounts)
- Row hover effect for visual feedback

**2.4 Update Member Role**

- Change a member's role within the organization
- Restricted to Admin/Owner users

**2.5 View Invitations**

- List pending invitations sent to users
- Invitation data includes: name, email, role, invited date, status

### Data Models

**OrganizationMemberApi:**

| Field         | Type           | Description          |
| ------------- | -------------- | -------------------- |
| `id`          | number         | Member record ID     |
| `user_id`     | number         | Associated user ID   |
| `name`        | string         | Member name          |
| `email`       | string         | Member email         |
| `role`        | string         | Role in organization |
| `joined_date` | string         | Date joined          |
| `avatar`      | string \| null | Avatar URL           |

**OrganizationInviteApi:**

| Field          | Type   | Description          |
| -------------- | ------ | -------------------- |
| `id`           | number | Invitation record ID |
| `name`         | string | Invitee name         |
| `email`        | string | Invitee email        |
| `role`         | string | Assigned role        |
| `invited_date` | string | Date invitation sent |
| `status`       | string | Invitation status    |

### API Endpoints

| Method | Endpoint                                   | Description              | Auth                     |
| ------ | ------------------------------------------ | ------------------------ | ------------------------ |
| GET    | `/api/v1/organizations/members`            | List all members         | `require_org_member`     |
| GET    | `/api/v1/organizations/invitations`        | List pending invitations | `require_org_member`     |
| POST   | `/api/v1/organizations/invite`             | Invite a user to the org | `require_admin_or_owner` |
| PATCH  | `/api/v1/organizations/members/{memberId}` | Update a member's role   | `require_admin_or_owner` |

### State Management (Jotai)

**Defined in:** `src/atoms/SettingsAtom.tsx`

| Atom                           | Type                  | Description                                        |
| ------------------------------ | --------------------- | -------------------------------------------------- |
| `loadableMembersRowsAtom`      | Read (async/loadable) | Fetches members list with loading/error states     |
| `loadableInvitationsRowsAtom`  | Read (async/loadable) | Fetches invitations list with loading/error states |
| `inviteUserToOrganizationAtom` | Write                 | Dispatches invite API call, triggers refetch       |
| `updateMemberRoleAtom`         | Write                 | Dispatches role update API call, triggers refetch  |
| `refetchMembersAtom`           | Write                 | Manually triggers members list refetch             |
| `refetchInvitationsAtom`       | Write                 | Manually triggers invitations list refetch         |

### Integration Status

- UI: Static mockup with hardcoded data
- State atoms: Defined but not connected to UI
- API service functions: Defined in `src/services/userService.ts` but not called

---

## 3. Organization Section

The Organization section manages access control settings for the organization.

**Rendered in:** `src/app/(dashboard)/settings/page.tsx` (inline)
**Title:** "Access Settings"

### Features

**3.1 Allow Users to Request Access (Toggle)**

- Toggle switch to enable/disable access requests during signup
- Label: "Allow users to request access"
- Description: "When enabled, users can request to join your organization during signup"
- Default: Enabled (true)

**3.2 Auto-Approve Same Email Domain (Nested Toggle)**

- Only visible when "Allow users to request access" is enabled
- Indented with a left border visual indicator
- Label: "Auto-approve users with same email domain"
- Description: "Automatically approve access requests from users with the same email domain"
- Default: Disabled (false)

**3.3 Handle Access Requests**

- Process incoming access requests (approve/deny)
- Expected payload: `{ request_id, action }`

**3.4 View Access Requests**

- List all pending access requests for the organization

### API Endpoints

| Method | Endpoint                                      | Description                  | Auth                     |
| ------ | --------------------------------------------- | ---------------------------- | ------------------------ |
| GET    | `/api/v1/organizations/settings`              | Fetch organization settings  | `require_org_member`     |
| PUT    | `/api/v1/organizations/settings`              | Update organization settings | `require_admin_or_owner` |
| GET    | `/api/v1/organizations/access_requests`       | List access requests         | `require_org_member`     |
| POST   | `/api/v1/organizations/handle_access_request` | Approve/deny a request       | `require_admin_or_owner` |

### Integration Status

- UI: Functional toggle switches with local state only
- No persistence to backend
- No loading of current settings from API on mount
- No save/submit mechanism

---

## 4. Web Hook Section

The Web Hook section is planned for configuring webhook endpoints for event notifications.

### Planned Features

- Configure webhook URLs for event callbacks
- Select which events trigger webhook notifications
- View webhook delivery history/logs
- Test webhook endpoints

### Integration Status

- Defined in sidebar navigation
- No UI component implemented
- No API endpoints defined

---

## Authentication & Authorization

### Route Protection

All settings routes are protected by middleware that requires a valid `tone_access_token` cookie.

### Role-Based Access Control

| Role       | Can View     | Can Edit     | Can Invite | Can Manage Keys |
| ---------- | ------------ | ------------ | ---------- | --------------- |
| **Owner**  | All sections | All settings | Yes        | Yes             |
| **Admin**  | All sections | All settings | Yes        | Yes             |
| **Member** | All sections | No           | No         | No              |

### Backend Auth Guards

| Guard                    | Description                          |
| ------------------------ | ------------------------------------ |
| `require_authenticated`  | Must be logged in                    |
| `require_org_member`     | Must be a member of the organization |
| `require_admin_or_owner` | Must have Admin or Owner role        |

### Frontend Role-Based UI

- Currently not implemented - all authenticated users see the same UI regardless of role
- **Needed:** Conditional rendering to hide action buttons (invite, delete, create key) for non-admin users

---

## Technical Architecture

### File Structure

```
frontend/src/
  app/(dashboard)/settings/
    page.tsx                          # Main settings page (route handler)

  components/settings/
    Apikeys.tsx                       # API Keys section (tab container)
    ApiKeysTab.tsx                    # API Keys tab content
    PublicKeysTab.tsx                 # Public Keys tab content
    SidebarComponent.tsx              # Settings sidebar navigation
    constants.tsx                     # Sidebar config & navigation items

  atoms/
    SettingsAtom.tsx                  # Jotai state atoms for members/invitations

  services/
    userService.ts                    # API service functions for members/invitations

  types/settings/
    members.ts                        # TypeScript interfaces
```

### Backend Endpoints (FastAPI)

```
core/api/v1/
  generated_api_keys.py               # API key CRUD endpoints
  organizations.py                    # Organization settings, members, invitations
```

### Technology Stack

| Layer             | Technology                         |
| ----------------- | ---------------------------------- |
| UI Framework      | React 19 + Next.js 15 (App Router) |
| Component Library | MUI 6 (Material-UI)                |
| Data Grid         | MUI DataGrid                       |
| State Management  | Jotai (with loadable utils)        |
| HTTP Client       | Axios (with auth interceptors)     |
| Icons             | Lucide React                       |
| Forms             | Controlled components (useState)   |

### Shared UI Patterns

**DataGrid Styling:**

- Gray column headers (`#e5e7eb` background)
- Uppercase, bold, 12px column titles
- Hidden column separators
- Row bottom borders
- Centered cell content

**Modal Dialogs:**

- MUI Dialog with custom padding (24px)
- Fixed width (450px)
- Title with close button (X icon)
- Footer with Cancel and Submit buttons
- Submit button: Black background, white text

**Color Scheme:**

- Primary accent: Purple (`#8b5cf6`)
- Neutral backgrounds: `#f9fafb`, `#f3f4f6`, `#e5e7eb`
- Button colors: Black (`#000`) with hover (`#333`)
- Error states: `theme.palette.error.main`

---

## Validation Rules

| Section     | Field        | Rule                           |
| ----------- | ------------ | ------------------------------ |
| API Keys    | Key Name     | Required, non-empty after trim |
| Public Keys | Key Name     | Required, non-empty            |
| Public Keys | Domains      | No duplicates allowed          |
| Members     | Invite Name  | Required                       |
| Members     | Invite Email | Required, valid email format   |
| Members     | Invite Role  | Required                       |

---

## Implementation Gaps & Roadmap

### High Priority

| Item                 | Section      | Description                                                     |
| -------------------- | ------------ | --------------------------------------------------------------- |
| Wire API Keys CRUD   | API Keys     | Connect create/reveal/delete to backend endpoints               |
| Wire Members list    | Members      | Connect to `loadableMembersRowsAtom` for live data              |
| Invite user modal    | Members      | Build invite form and connect to `inviteUserToOrganizationAtom` |
| Persist org settings | Organization | Load settings on mount, save on toggle change                   |
| Role-based UI guards | All          | Hide admin actions for non-admin users                          |

### Medium Priority

| Item                 | Section | Description                                |
| -------------------- | ------- | ------------------------------------------ |
| Delete member        | Members | Implement member removal with confirmation |
| Role change dropdown | Members | Inline role editing for admin/owner        |
| Invitations list     | Members | Show pending invitations with status       |
| Loading states       | All     | Add spinners/skeletons during API calls    |
| Error handling       | All     | Toast notifications for failed operations  |
| Empty states         | All     | Show placeholder UI when no data exists    |

### Low Priority

| Item                 | Section      | Description                                    |
| -------------------- | ------------ | ---------------------------------------------- |
| Web Hook UI          | Web Hook     | Build complete webhook configuration section   |
| Search members       | Members      | Wire search input to filter functionality      |
| Pagination           | Members/Keys | Handle large lists with server-side pagination |
| Audit log            | All          | Track changes to settings for compliance       |
| Key expiration       | API Keys     | Set TTL on API keys with auto-rotation         |
| Webhook retry config | Web Hook     | Configure retry policies for failed deliveries |

---

## User Flows

### Flow 1: Create an API Key

```
1. Navigate to /settings
2. "API Key" section is active by default
3. Click "Add Key" button
4. Enter a name for the key in the modal
5. Click "Add" to create
6. Key appears in the table (masked)
7. Use row menu > "Reveal Key" to see the full value
```

### Flow 2: Invite a Team Member

```
1. Navigate to /settings
2. Click "Members" in the sidebar
3. Click "Invite user" button
4. Enter name, email, and role
5. Submit the invitation
6. Invited user appears in pending invitations list
7. User receives invitation email
8. Upon acceptance, user moves to active members list
```

### Flow 3: Configure Organization Access

```
1. Navigate to /settings
2. Click "Organization" in the sidebar
3. Toggle "Allow users to request access" on/off
4. If enabled, optionally toggle "Auto-approve same email domain"
5. Settings persist automatically
```

### Flow 4: Create a Public Key with Domain Restrictions

```
1. Navigate to /settings
2. "API Key" section is active by default
3. Click "Public Keys" tab
4. Click "Add Key" button
5. Enter key name
6. Add allowed domains one by one (type + Enter)
7. Enable/disable Abuse Prevention (reCAPTCHA)
8. Enable/disable Fraud Protection
9. Click "Add" to create
10. Key appears in the table with domain and security status
```

---

## API Request/Response Examples

### List Organization Members

```
GET /api/v1/organizations/members
Headers:
  Authorization: Bearer <token>
  tenant_id: <org_tenant_id>

Response 200:
[
  {
    "id": 1,
    "user_id": 42,
    "name": "Karthik",
    "email": "karthik@productfusion.co",
    "role": "owner",
    "joined_date": "2025-01-15T10:00:00Z",
    "avatar": null
  }
]
```

### Invite User to Organization

```
POST /api/v1/organizations/invite
Headers:
  Authorization: Bearer <token>
  tenant_id: <org_tenant_id>
Body:
{
  "name": "John Doe",
  "email": "john@example.com",
  "role": "member"
}

Response 200: (success)
```

### Update Organization Settings

```
PUT /api/v1/organizations/settings
Headers:
  Authorization: Bearer <token>
  tenant_id: <org_tenant_id>
Body:
{
  "allow_access_requests": true,
  "auto_approve_same_domain": false
}

Response 200: (success)
```

### Handle Access Request

```
POST /api/v1/organizations/handle_access_request
Headers:
  Authorization: Bearer <token>
  tenant_id: <org_tenant_id>
Body:
{
  "request_id": 5,
  "action": "approve"
}

Response 200: (success)
```
