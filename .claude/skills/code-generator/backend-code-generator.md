# Backend Coding Standards
Always write production-ready, maintainable, and scalable code.

## Core Principles

- Follow SOLID, DRY principles.
- Prioritize readability over cleverness.
- Keep functions and classes focused on a single responsibility.
- Prefer composition over inheritance.
- Reuse existing code instead of duplicating logic.
- Match the existing project architecture and coding style.

---

## 🚨 Critical Rule: Service Layer

This is the most important architectural rule in this project.

The Service layer is the single source of truth for all business logic.

**Always design services as reusable, transport-agnostic components.** Assume every service you write will be reused by:

- APIs
- Background jobs
- Scheduled/Cron jobs
- Event consumers
- CLI commands
- Future integrations

The Service layer **must never** depend on HTTP requests, responses, status codes, route handlers, or any API-specific concepts.

The API layer should only:

- Validate requests
- Handle authentication/authorization
- Call service methods
- Return HTTP responses

Before writing business logic, always ask:

> "Can this logic be reused elsewhere?"

If yes (which is almost always the case), implement it in the Service layer—not the API layer.

---

## Database

- Avoid N+1 queries.
- Fetch only the required data.
- Optimize queries before writing them.
- Prefer bulk operations when appropriate.

---

## Code Quality

- Use meaningful names.
- Keep functions small and focused.
- Handle errors gracefully.
- Add useful logs, but never log secrets or sensitive data.
- Never hardcode configuration, secrets, or environment-specific values.

---

## Before Returning Code

Verify that:

- Business logic exists only in the Service layer.
- No duplicated logic exists.
- Code follows SOLID, DRY.
- Database queries are efficient.
- Validation and error handling are complete.
- The implementation is clean, reusable, maintainable, and production-ready.

If there is a better architectural approach than the requested implementation, explain it before implementing.


---

## Backend Validation & Enforcement

Never rely on frontend validation or UI restrictions to enforce business rules.

Any request may originate from:

- Frontend applications
- CLI tools
- cURL/Postman
- External APIs
- Background jobs
- Scheduled/Cron jobs
- Event consumers
- Future integrations

All business rules, permissions, validations, and security checks must be enforced in the backend, regardless of the client making the request.

Frontend validation should only improve the user experience and provide early feedback—it must never be treated as the source of truth.

If a rule is important enough to exist, it must be enforced in the backend.