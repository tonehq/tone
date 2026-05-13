---
name: provisioning-db
description: "Provision a new Neon database and configure Infisical secrets for a deployment environment. Use when setting up a new environment that needs a database (e.g., after running /setup-new-deployment) or when the user asks to create a database, provision DB, or set up Infisical secrets for an environment."
---

# Provisioning DB

Create a Neon database using the neonctl CLI and configure Infisical secrets via infisical CLI.

**Pattern:**
- Use AskUserQuestion for ALL user choices
- Run all CLI commands via Bash — chain related commands in a single Bash call to minimize permission prompts
- neonctl commands MUST include `--org-id <ORG_ID>` to skip interactive org selection
- Infisical domain is NOT hardcoded — read from `~/.infisical/infisical-config.json` > `LoggedInUserDomain`. If not found, ask user via AskUserQuestion (options: `https://secrets.trytone.ai`, `https://app.infisical.com`, + "Other")
- infisical CLI commands MUST include `--domain <DOMAIN>` with the user's chosen/detected domain
- Infisical CLI does NOT have commands for listing projects or creating environments — use the Infisical REST API with JWT from macOS Keychain
- Infisical JWT is stored in macOS Keychain under service `infisical-cli` with account name = user email (read from `~/.infisical/infisical-config.json` > `loggedInUserEmail`)
- Infisical `secrets set` does NOT allow empty values — use `REPLACE_ME` as placeholder for skipped secrets

## Scripts

Both helper scripts are in `scripts/` directory of this skill:
- `scripts/neon_api.py` — wraps neonctl commands, outputs JSON
- `scripts/infisical_api.py` — handles Infisical API via JWT from Keychain

Set the script path variable:
```bash
SKILL_DIR=".claude/skills/provisioning-db/scripts"
```

## Step 1: Check Prerequisites

```bash
python3 $SKILL_DIR/neon_api.py check && python3 $SKILL_DIR/infisical_api.py auth-check
```

- If neonctl missing: display `! npm i -g neonctl && neonctl auth` and STOP.
- If infisical missing: display `! brew install infisical/get-cli/infisical` and STOP.
- If infisical auth expired: display login commands (see Step 6) and STOP.
- If both ok: proceed.

## Step 2: Select Organization

```bash
python3 $SKILL_DIR/neon_api.py list-orgs
```

Parse JSON. Use AskUserQuestion to show all orgs PLUS "Create new organization". Always show chooser even if only one org.
- If "Create new": user types org name via "Other". Tell them to run `! neonctl orgs create --name <NAME>` and re-list.

Capture `ORG_ID`.

## Step 3: Select or Create Project

```bash
python3 $SKILL_DIR/neon_api.py list-projects --org-id <ORG_ID>
```

Use AskUserQuestion to show projects PLUS "Create new project".

**If "Create new":** use AskUserQuestion to collect (3 questions):
1. **Project name** — options: `{project}-dev-testing`, `{project}-staging` + "Other"
2. **Postgres version** — options: `17 (Recommended)`, `16`, `15`, `14`
3. **Region** — fetch available regions dynamically:
     ```bash
     python3 $SKILL_DIR/neon_api.py list-regions
     ```
     Print all regions as a numbered list in text output. Then use AskUserQuestion — show top 3 popular regions as options + "Other" for typing region ID from the list. AskUserQuestion has a max of 4 options per question.

Then create:
```bash
python3 $SKILL_DIR/neon_api.py create-project --org-id <ORG_ID> --name <NAME> --region <REGION>
```

**If existing:** use selected project ID.

Get branch ID:
```bash
python3 $SKILL_DIR/neon_api.py list-branches --project-id <PROJECT_ID>
```

## Step 4: Create Role & Database

Use AskUserQuestion (2 questions):
1. **Role name** — options: `{project}_{env}_user` + "Other"
2. **Database name** — options: `{project}_{env}` + "Other"

```bash
python3 $SKILL_DIR/neon_api.py create-role --project-id <PID> --branch-id <BID> --name <ROLE>
python3 $SKILL_DIR/neon_api.py create-database --project-id <PID> --branch-id <BID> --name <DB> --owner <ROLE>
```

If status=exists, continue (not an error).

## Step 5: Get Connection String

```bash
python3 $SKILL_DIR/neon_api.py connection-string --project-id <PID> --database <DB> --role <ROLE>
```

Returns parsed JSON with `DATABASE_URL`, `DB_HOST`, `DB_PORT`, `DB_NAME`, `DB_USER`, `DB_PASSWORD`.
Display values to user.

## Step 6: Infisical Auth

Use the helper script at `scripts/infisical_api.py` (in this skill's directory) for all Infisical API calls.

```bash
SCRIPT=".claude/skills/provisioning-db/scripts/infisical_api.py"
python3 $SCRIPT auth-check
```

- If `status=ok`: proceed.
- If `status=expired` or `status=no_config`: login automatically. Use AskUserQuestion to collect (3 questions):
  1. **Infisical domain** — options: auto-detected domain from auth-check output if available, `https://secrets.trytone.ai`, `https://app.infisical.com` + "Other"
  2. **Email** — options: auto-detected email from auth-check output if available + "Other"
  3. **Password** — "Type password in notes" (user types in notes field)

  Then login via script:
  ```bash
  python3 $SCRIPT login --email <EMAIL> --password <PASSWORD> --domain <DOMAIN>
  ```

  After login, re-run `python3 $SCRIPT auth-check` to verify.

## Step 7: Select Infisical Org & Project

**7a. List orgs:**
```bash
python3 $SCRIPT list-orgs
```
Use AskUserQuestion to show all orgs. Always show chooser even if only one org (same pattern as Neon). Capture `INFISICAL_ORG_ID`.

**If "Create new org":** Ask org name via AskUserQuestion. Then create:
```bash
python3 $SCRIPT create-org --name <ORG_NAME>
```

**7b. List projects:**
```bash
python3 $SCRIPT list-projects --org-id <INFISICAL_ORG_ID>
```
Use AskUserQuestion to show projects PLUS "Create new project".

**If "Create new":** Ask project name via AskUserQuestion. Then create:
```bash
python3 $SCRIPT create-project --org-id <INFISICAL_ORG_ID> --name <PROJECT_NAME>
```

**If existing:** Use selected project ID.

Capture `INFISICAL_PROJECT_ID`.

## Step 8: Select or Create Environment

**8a. List environments:**
```bash
python3 $SCRIPT list-envs --project-id <INFISICAL_PROJECT_ID>
```
Use AskUserQuestion to show existing environments PLUS "Create new environment".

**8b. If "Create new":** Ask for environment name via AskUserQuestion (options: `dev-testing`, `staging`, `production` + "Other"). Then create:
```bash
python3 $SCRIPT create-env --project-id <INFISICAL_PROJECT_ID> --name <ENV_NAME> --slug <ENV_NAME>
```

**If existing:** Use the selected environment slug as ENV_NAME.

## Step 9: Generate SECRET_KEY & Set Infisical Secrets

Run ALL in a single Bash call:

```bash
SECRET_KEY=$(python3 -c "import secrets; print(secrets.token_hex(32))") && \
infisical secrets set \
  "DATABASE_URL={actual}" \
  "DB_HOST={actual}" \
  "DB_PORT=5432" \
  "DB_NAME={actual}" \
  "DB_USER={actual}" \
  "DB_PASSWORD={actual}" \
  "SECRET_KEY=$SECRET_KEY" \
  "IS_MULTI_TENANT=false" \
  "USE_INFISICAL=true" \
  --env {ENV_NAME} \
  --projectId {INFISICAL_PROJECT_ID} \
  --domain {INFISICAL_DOMAIN}
```

Display the result to user.

## Step 10: Create Infisical Service Token

Use AskUserQuestion to ask for the token name (options: `{project}-{ENV_NAME}`, `{ENV_NAME}-service-token` + "Other").

Then create via script:
```bash
python3 $SKILL_DIR/infisical_api.py create-service-token \
  --project-id <INFISICAL_PROJECT_ID> \
  --env <ENV_NAME> \
  --name <TOKEN_NAME>
```

Returns JSON with `token` field. Capture `INFISICAL_TOKEN`.

## Step 11: Summary

Display the full summary with all actual values. Do NOT run any commands — just print for the user.

```
Neon Database:
  Project:      {project_name} ({project_id})
  Region:       {region}
  Database:     {DB_NAME}
  Role:         {DB_USER}
  DATABASE_URL: {actual DATABASE_URL}

Infisical:
  Project:      {infisical_project_name} ({INFISICAL_PROJECT_ID})
  Environment:  {ENV_NAME}
  Secrets:      {count} secrets set
  Token:        {INFISICAL_TOKEN}

K8s Secret:
  kubectl create namespace {ENV_NAME} --dry-run=client -o yaml | kubectl apply -f -

  kubectl create secret generic infisical-credentials \
    --namespace={ENV_NAME} \
    --from-literal=token='{actual INFISICAL_TOKEN}' \
    --from-literal=project_id='{actual INFISICAL_PROJECT_ID}' \
    --dry-run=client -o yaml | kubectl apply -f -

Migrations:
  export DATABASE_URL='{actual DATABASE_URL}'
  alembic upgrade head
  python dev/seed.py

Verify:
  kubectl get secrets -n {ENV_NAME}
  kubectl get pods -n {ENV_NAME}
```
