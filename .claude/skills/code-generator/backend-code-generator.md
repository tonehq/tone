# Backend Coding Standards

Always write production-ready, maintainable, and scalable code.

## Core Principles

- Follow SOLID and DRY principles.
- Prioritize readability over cleverness.
- Keep functions and classes focused on a single responsibility.
- Prefer composition over inheritance.
- Reuse existing code instead of duplicating logic.
- Match the existing project architecture and coding style.

## OOP Principles

- Follow core Object-Oriented Programming principles where appropriate.
- Use encapsulation to keep data and related behavior together and control access to internal implementation details.
- Use abstraction to hide unnecessary implementation details and expose clear interfaces.
- Use polymorphism when multiple implementations need to follow the same interface or contract.
- Use inheritance only when there is a genuine "is-a" relationship.
- Prefer composition over inheritance when it provides better flexibility and maintainability.
- Keep classes focused on a single responsibility.
- Avoid unnecessary classes, deep inheritance hierarchies, and overly complex abstractions.

---

## 🚨 Critical Rule: Service Layer

The Service layer is the single source of truth for all business logic.

Always design services as reusable, transport-agnostic components. Assume every service will be reused by:

- APIs
- Background jobs
- Scheduled/Cron jobs
- Event consumers
- CLI commands
- Future integrations

The Service layer must NEVER depend on:

- HTTP requests
- HTTP responses
- HTTP status codes
- Route handlers
- API-specific concepts
- Frontend-specific logic

The API layer should only:

- Validate requests
- Handle authentication/authorization
- Call service methods
- Convert service/application errors into appropriate HTTP responses
- Return responses to the client

Before writing business logic, always ask:

"Can this logic be reused elsewhere?"

If yes, implement it in the Service layer, not the API layer.

---

## 🚨 Error Handling

Error handling must be consistent across the entire backend.

### General Rules

- Always handle errors appropriately.
- Do not use try/except everywhere unnecessarily.
- Use try/except when the error can be meaningfully handled, transformed, logged, or recovered from.
- Catch specific exceptions whenever possible instead of using a broad `except Exception`.
- Never silently ignore errors.
- Never use empty except blocks.
- Never expose raw exceptions, stack traces, database errors, SQL queries, internal implementation details, or sensitive information to the frontend.

### Service Layer Errors

- Business and domain errors must be handled in the Service layer.
- Services should raise meaningful application-specific exceptions for expected business failures.
- Do NOT raise HTTP-specific exceptions such as `HTTPException` from the Service layer.
- Service exceptions must be reusable regardless of whether the caller is an API, background job, CLI, event consumer, or scheduled job.
- Use clear, meaningful exception types such as:
  - `UserNotFoundError`
  - `ResourceAlreadyExistsError`
  - `InsufficientPermissionError`
  - `InvalidOperationError`

### API Error Handling

The API layer is responsible for converting application/service errors into HTTP responses.

The expected flow is:

Service
    ↓
Business condition fails
    ↓
Raise application-specific exception
    ↓
API / Global Exception Handler
    ↓
Convert to HTTP status + safe message
    ↓
Frontend

The frontend should receive a simple and clear message that can safely be shown to the user.

Example:

{
  "error": {
    "code": "USER_NOT_FOUND",
    "message": "User not found."
  }
}

Do NOT return messages such as:

- `psycopg2.errors.UniqueViolation...`
- `SQLAlchemy IntegrityError...`
- Raw database errors
- Stack traces
- File names or line numbers
- Internal implementation details

Instead, return a clear user-friendly message.

For example:

{
  "error": {
    "code": "EMAIL_ALREADY_EXISTS",
    "message": "An account with this email already exists."
  }
}

### Unexpected Errors

- Unexpected/unhandled errors must be handled by a global exception handler.
- Log the complete technical error on the backend for debugging.
- Return a generic, safe message to the frontend.
- Never expose internal implementation details to users.

Example:

{
  "error": {
    "code": "INTERNAL_SERVER_ERROR",
    "message": "Something went wrong. Please try again later."
  }
}

### Logging

- Log useful technical information when handling unexpected errors.
- Include enough context to debug the problem.
- Never log passwords, tokens, API keys, secrets, or sensitive user information.
- Do not expose backend logs to the frontend.

### Error Response Consistency

Use a consistent error response structure across APIs.

Example:

{
  "error": {
    "code": "RESOURCE_NOT_FOUND",
    "message": "The requested resource was not found."
  }
}

Where:

- `code` is a stable machine-readable error code.
- `message` is a simple human-readable message suitable for displaying to the user.

The frontend should not need to understand backend implementation details to display an error.

### Validation Errors

- Validate all input on the backend.
- Never rely on frontend validation.
- Return clear validation messages that explain what the user needs to correct.
- Validation errors should identify the relevant field when appropriate.

Example:

{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Please enter a valid email address."
  }
}

---

## Database

- Avoid N+1 queries.
- Fetch only the required data.
- Optimize queries before writing them.
- Prefer bulk operations when appropriate.
- Handle database exceptions appropriately.
- Never expose raw database errors to the frontend.

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

Frontend validation should only improve the user experience and provide early feedback. It must never be treated as the source of truth.

If a rule is important enough to exist, it must be enforced in the backend.

---

## Code Quality

- Use meaningful names.
- Keep functions small and focused.
- Handle errors gracefully.
- Add useful logs, but never log secrets or sensitive data.
- Never hardcode configuration, secrets, or environment-specific values.
- Avoid unnecessary try/except blocks.
- Avoid duplicated error-handling logic.
- Use reusable exception classes and centralized exception handling where appropriate.

---

## Before Returning Code

Verify that:

- Business logic exists only in the Service layer.
- No duplicated logic exists.
- Code follows SOLID and DRY principles.
- Database queries are efficient.
- Validation and error handling are complete.
- Expected business errors are represented using meaningful application exceptions.
- Services do not depend on HTTP-specific concepts.
- API/global handlers convert application errors into appropriate HTTP responses.
- Frontend receives simple, clear, user-friendly error messages.
- Raw exceptions and sensitive implementation details are never exposed to the frontend.
- Unexpected errors are logged properly and return a safe generic message.
- Error responses follow a consistent structure.
- The implementation is clean, reusable, maintainable, and production-ready.