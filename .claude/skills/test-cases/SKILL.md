Analyze the SKILL.md file inside the generate-api-code-documentation folder and generate pytest test cases based on it.

Create separate test files for each controller.

Cover every API endpoint.

For each API, include all possible test cases (success, failure, edge cases, validation errors, etc.).

Structure the test cases cleanly so they are ready to run directly.

Update Logic for Future Runs

The SKILL.md file will be updated whenever APIs are added, modified, or deleted.

On the first run, generate test cases for all APIs.

On subsequent runs:

Detect which APIs were added, edited, or removed.

Update or modify test cases only for those affected APIs.

Do not regenerate test cases for unchanged APIs.

Change Detection Rules

To do this:

Track the last execution time of this skill.

Compare:

Git differences since the last execution.

Local code changes (even if not committed).

Identify only the affected APIs.

Update test cases accordingly.

Important Constraints

Do not duplicate test cases.

Ensure changes from both git differences and local modifications are handled.

Do not re-check or rewrite all APIs every time.

Only modify what is necessary.