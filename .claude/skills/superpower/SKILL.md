---
name: superpowers
description: Unlocks Claude's maximum capability across full-stack Next.js + TypeScript development, AI agent & prompt engineering, system design & architecture, and deep code review & refactoring. Use this skill for any serious engineering task where quality, correctness, and production-readiness matter.
version: 1.0.0
stack: Next.js + TypeScript
---

This skill activates Claude's highest-quality engineering mode. Every output must be production-grade, type-safe, performant, and maintainable. No shortcuts. No placeholder code. No "TODO: implement this". Deliver complete, working solutions.

---

## 0. Core Operating Principles

Before writing a single line of code:

1. **Understand before building** — Restate the goal, identify edge cases, surface assumptions.
2. **Design before coding** — Sketch the data model, API contract, and component tree first.
3. **Type everything** — No `any`, no `unknown` without narrowing, no implicit returns.
4. **Fail loudly** — Prefer explicit errors over silent failures. Throw early, catch at the boundary.
5. **Ship complete code** — Every function, component, and handler must be fully implemented. Never leave stub implementations.

---

## 1. Full-Stack Code Generation — Next.js + TypeScript

### Project Structure (App Router)
```
src/
├── app/
│   ├── (auth)/           # Route groups
│   │   ├── login/
│   │   └── signup/
│   ├── (dashboard)/
│   │   ├── layout.tsx
│   │   └── page.tsx
│   ├── api/              # Route handlers
│   │   └── [resource]/
│   │       └── route.ts
│   ├── globals.css
│   ├── layout.tsx        # Root layout
│   └── page.tsx
├── components/
│   ├── ui/               # shadcn/ui primitives
│   └── [feature]/        # Feature-specific components
├── lib/
│   ├── db/               # Database client & queries
│   ├── auth/             # Auth utilities
│   ├── validations/      # Zod schemas
│   └── utils.ts          # cn() and helpers
├── hooks/                # Custom React hooks
├── types/                # Global TypeScript types
├── actions/              # Server Actions
└── middleware.ts
```

### TypeScript Standards

```ts
// NEVER use `any` — use proper generics or unknown with narrowing
type ApiResponse<T> = {
  data: T
  error: null
} | {
  data: null
  error: { message: string; code: string }
}

// Always define explicit return types on exported functions
export async function getUser(id: string): Promise<User | null> { ... }

// Use discriminated unions for state
type RequestState<T> =
  | { status: 'idle' }
  | { status: 'loading' }
  | { status: 'success'; data: T }
  | { status: 'error'; error: string }

// Prefer type over interface for data shapes
type User = {
  id: string
  email: string
  name: string
  createdAt: Date
}

// Use interface for things that will be extended/implemented
interface Repository<T> {
  findById(id: string): Promise<T | null>
  findMany(filters: Partial<T>): Promise<T[]>
  create(data: Omit<T, 'id' | 'createdAt'>): Promise<T>
  update(id: string, data: Partial<T>): Promise<T>
  delete(id: string): Promise<void>
}

// Zod for ALL external data — API inputs, form data, env vars
import { z } from 'zod'

const UserSchema = z.object({
  id: z.string().cuid(),
  email: z.string().email(),
  name: z.string().min(1).max(100),
  role: z.enum(['admin', 'user', 'viewer']),
  createdAt: z.coerce.date(),
})
type User = z.infer<typeof UserSchema>

// Environment variables — always validated
const envSchema = z.object({
  DATABASE_URL: z.string().url(),
  NEXTAUTH_SECRET: z.string().min(32),
  NEXTAUTH_URL: z.string().url(),
  OPENAI_API_KEY: z.string().startsWith('sk-'),
})
export const env = envSchema.parse(process.env)
```

### App Router Patterns

```tsx
// Server Component (default) — fetch data directly, no useEffect
// app/dashboard/page.tsx
import { db } from '@/lib/db'
import { auth } from '@/lib/auth'
import { redirect } from 'next/navigation'

export default async function DashboardPage() {
  const session = await auth()
  if (!session) redirect('/login')

  const data = await db.query.users.findMany({
    where: eq(users.orgId, session.user.orgId),
    orderBy: desc(users.createdAt),
  })

  return <UserTable data={data} />
}

// Client Component — only when you need interactivity
'use client'
import { useState, useTransition } from 'react'

export function DeleteButton({ id }: { id: string }) {
  const [isPending, startTransition] = useTransition()

  return (
    <Button
      variant="destructive"
      disabled={isPending}
      onClick={() => startTransition(() => deleteUser(id))}
    >
      {isPending ? <Spinner /> : 'Delete'}
    </Button>
  )
}

// Route Handler — typed, validated, error-handled
// app/api/users/route.ts
import { NextRequest, NextResponse } from 'next/server'
import { z } from 'zod'
import { db } from '@/lib/db'
import { auth } from '@/lib/auth'

const CreateUserSchema = z.object({
  email: z.string().email(),
  name: z.string().min(1).max(100),
  role: z.enum(['admin', 'user', 'viewer']).default('user'),
})

export async function POST(req: NextRequest) {
  try {
    const session = await auth()
    if (!session) {
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })
    }

    const body = await req.json()
    const parsed = CreateUserSchema.safeParse(body)
    if (!parsed.success) {
      return NextResponse.json(
        { error: 'Validation failed', details: parsed.error.flatten() },
        { status: 400 }
      )
    }

    const user = await db.insert(users).values(parsed.data).returning()
    return NextResponse.json({ data: user[0] }, { status: 201 })
  } catch (error) {
    console.error('[POST /api/users]', error)
    return NextResponse.json({ error: 'Internal Server Error' }, { status: 500 })
  }
}

// Server Actions — for form submissions and mutations
// actions/users.ts
'use server'
import { revalidatePath } from 'next/cache'
import { redirect } from 'next/navigation'
import { auth } from '@/lib/auth'
import { db } from '@/lib/db'
import { z } from 'zod'

const UpdateUserSchema = z.object({
  id: z.string().cuid(),
  name: z.string().min(1).max(100),
  role: z.enum(['admin', 'user', 'viewer']),
})

export async function updateUser(formData: FormData) {
  const session = await auth()
  if (!session) redirect('/login')

  const parsed = UpdateUserSchema.safeParse({
    id: formData.get('id'),
    name: formData.get('name'),
    role: formData.get('role'),
  })
  if (!parsed.success) {
    return { error: parsed.error.flatten().fieldErrors }
  }

  await db.update(users)
    .set({ name: parsed.data.name, role: parsed.data.role })
    .where(eq(users.id, parsed.data.id))

  revalidatePath('/dashboard/users')
  return { success: true }
}
```

### Database Layer (Drizzle ORM — recommended)

```ts
// lib/db/schema.ts
import { pgTable, text, timestamp, uuid, pgEnum } from 'drizzle-orm/pg-core'

export const roleEnum = pgEnum('role', ['admin', 'user', 'viewer'])

export const users = pgTable('users', {
  id: uuid('id').defaultRandom().primaryKey(),
  email: text('email').notNull().unique(),
  name: text('name').notNull(),
  role: roleEnum('role').notNull().default('user'),
  orgId: uuid('org_id').notNull().references(() => orgs.id, { onDelete: 'cascade' }),
  createdAt: timestamp('created_at').defaultNow().notNull(),
  updatedAt: timestamp('updated_at').defaultNow().notNull(),
})

// lib/db/index.ts
import { drizzle } from 'drizzle-orm/postgres-js'
import postgres from 'postgres'
import * as schema from './schema'
import { env } from '@/lib/env'

const client = postgres(env.DATABASE_URL)
export const db = drizzle(client, { schema })

// lib/db/queries/users.ts — always colocate queries with schema
export async function getUsersByOrg(orgId: string) {
  return db.query.users.findMany({
    where: eq(users.orgId, orgId),
    orderBy: desc(users.createdAt),
    with: { org: true },
  })
}
```

### Custom Hooks Pattern

```ts
// hooks/use-async-action.ts
import { useState, useCallback } from 'react'

type AsyncState<T> =
  | { status: 'idle' }
  | { status: 'loading' }
  | { status: 'success'; data: T }
  | { status: 'error'; error: string }

export function useAsyncAction<TArgs extends unknown[], TReturn>(
  action: (...args: TArgs) => Promise<TReturn>
) {
  const [state, setState] = useState<AsyncState<TReturn>>({ status: 'idle' })

  const execute = useCallback(async (...args: TArgs) => {
    setState({ status: 'loading' })
    try {
      const data = await action(...args)
      setState({ status: 'success', data })
      return data
    } catch (err) {
      const error = err instanceof Error ? err.message : 'Unknown error'
      setState({ status: 'error', error })
      throw err
    }
  }, [action])

  const reset = useCallback(() => setState({ status: 'idle' }), [])

  return { state, execute, reset }
}
```

---

## 2. AI Agent & Prompt Engineering Patterns

### Structured Output Pattern (Vercel AI SDK)

```ts
import { generateObject, generateText, streamText } from 'ai'
import { openai } from '@ai-sdk/openai'
import { anthropic } from '@ai-sdk/anthropic'
import { z } from 'zod'

// Always use generateObject for structured data
const ExtractionSchema = z.object({
  entities: z.array(z.object({
    name: z.string(),
    type: z.enum(['person', 'org', 'location', 'date']),
    confidence: z.number().min(0).max(1),
  })),
  summary: z.string().max(200),
  sentiment: z.enum(['positive', 'negative', 'neutral']),
})

export async function extractEntities(text: string) {
  const { object } = await generateObject({
    model: openai('gpt-4o'),
    schema: ExtractionSchema,
    prompt: `Extract all named entities from the following text:\n\n${text}`,
  })
  return object
}

// Streaming for long-form generation
export async function streamResponse(prompt: string) {
  const result = await streamText({
    model: anthropic('claude-3-5-sonnet-20241022'),
    system: 'You are a helpful assistant.',
    messages: [{ role: 'user', content: prompt }],
    maxTokens: 2048,
  })
  return result.toDataStreamResponse()
}
```

### Agent Loop Pattern

```ts
// lib/agents/base-agent.ts
type Tool<TInput, TOutput> = {
  name: string
  description: string
  schema: z.ZodType<TInput>
  execute: (input: TInput) => Promise<TOutput>
}

type AgentConfig = {
  model: string
  systemPrompt: string
  tools: Tool<unknown, unknown>[]
  maxIterations?: number
}

export async function runAgent(
  config: AgentConfig,
  userMessage: string,
): Promise<string> {
  const { model, systemPrompt, tools, maxIterations = 10 } = config
  const messages: CoreMessage[] = [{ role: 'user', content: userMessage }]

  for (let i = 0; i < maxIterations; i++) {
    const { text, toolCalls, finishReason } = await generateText({
      model: openai(model),
      system: systemPrompt,
      messages,
      tools: Object.fromEntries(
        tools.map(t => [t.name, { description: t.description, parameters: t.schema }])
      ),
    })

    if (finishReason === 'stop') return text

    // Execute tool calls in parallel
    const toolResults = await Promise.all(
      toolCalls.map(async call => {
        const tool = tools.find(t => t.name === call.toolName)
        if (!tool) throw new Error(`Unknown tool: ${call.toolName}`)
        const result = await tool.execute(call.args)
        return { toolCallId: call.toolCallId, result }
      })
    )

    messages.push({ role: 'assistant', content: toolCalls })
    messages.push({ role: 'tool', content: toolResults })
  }

  throw new Error(`Agent exceeded max iterations (${maxIterations})`)
}
```

### Prompt Engineering Standards

```ts
// lib/prompts/templates.ts

// Use XML tags for structured prompting (best practice for Claude)
export function buildAnalysisPrompt(context: string, question: string): string {
  return `
<context>
${context}
</context>

<task>
${question}
</task>

<instructions>
- Answer based only on the information in <context>
- If the answer is not in the context, say "I don't have enough information"
- Be concise and specific
- Format your response as structured JSON
</instructions>
`.trim()
}

// Few-shot prompting
export function buildClassificationPrompt(examples: Array<{input: string; label: string}>, input: string): string {
  const exampleBlock = examples.map(e =>
    `Input: ${e.input}\nLabel: ${e.label}`
  ).join('\n\n')

  return `Classify the following input. Here are examples:\n\n${exampleBlock}\n\nInput: ${input}\nLabel:`
}

// Chain-of-thought
export const COT_SUFFIX = `\n\nThink step by step before giving your final answer. Show your reasoning.`

// Prompt versioning — always version your prompts
export const PROMPTS = {
  'extract-v1': { version: 1, template: '...' },
  'extract-v2': { version: 2, template: '...' },
} as const
```

### RAG Pattern

```ts
// lib/rag/retriever.ts
import { embed, embedMany } from 'ai'
import { openai } from '@ai-sdk/openai'

export async function indexDocuments(docs: Array<{ id: string; content: string }>) {
  const { embeddings } = await embedMany({
    model: openai.embedding('text-embedding-3-small'),
    values: docs.map(d => d.content),
  })

  // Store in vector DB (pgvector / Pinecone / etc.)
  await db.insert(embeddings_table).values(
    docs.map((doc, i) => ({
      id: doc.id,
      content: doc.content,
      embedding: embeddings[i],
    }))
  )
}

export async function retrieve(query: string, topK = 5) {
  const { embedding } = await embed({
    model: openai.embedding('text-embedding-3-small'),
    value: query,
  })

  return db.select()
    .from(embeddings_table)
    .orderBy(cosineDistance(embeddings_table.embedding, embedding))
    .limit(topK)
}
```

---

## 3. System Design & Architecture

### Decision Framework

For every system design task, answer these before proposing a solution:

1. **Scale**: How many users? Requests/sec? Data volume? Growth rate?
2. **Consistency vs Availability**: Can we serve stale data? What's the cost of a write conflict?
3. **Latency budget**: P50/P95/P99 requirements? User-facing or background?
4. **Failure modes**: What breaks if the DB goes down? If a queue is full? If an API is slow?
5. **Operational complexity**: Who maintains this? What's the team's expertise?

### Architecture Patterns for Next.js Apps

```
┌─────────────────────────────────────────────────────────┐
│  Next.js App (Vercel / Railway / Fly.io)                 │
│  ┌──────────────┐  ┌──────────────┐  ┌───────────────┐  │
│  │  App Router  │  │   API Routes │  │ Server Actions│  │
│  │  (RSC + CC)  │  │  (REST/RPC)  │  │  (mutations)  │  │
│  └──────┬───────┘  └──────┬───────┘  └───────┬───────┘  │
└─────────┼────────────────┼───────────────────┼──────────┘
          │                │                   │
          ▼                ▼                   ▼
┌────────────────────────────────────────────────────────┐
│  Data Layer                                             │
│  ┌───────────┐  ┌──────────┐  ┌──────┐  ┌──────────┐  │
│  │ PostgreSQL│  │  Redis   │  │ S3   │  │  Queue   │  │
│  │ (Drizzle) │  │ (cache)  │  │(files│  │(BullMQ)  │  │
│  └───────────┘  └──────────┘  └──────┘  └──────────┘  │
└────────────────────────────────────────────────────────┘
```

### Caching Strategy

```ts
// lib/cache.ts — layered caching
import { unstable_cache } from 'next/cache'
import { Redis } from '@upstash/redis'

const redis = new Redis({ url: env.UPSTASH_URL, token: env.UPSTASH_TOKEN })

// Layer 1: Next.js full route cache (static)
// Layer 2: React cache (per-request deduplication)
// Layer 3: Redis (cross-request, distributed)
// Layer 4: DB query cache

export const getCachedUser = unstable_cache(
  async (id: string) => db.query.users.findFirst({ where: eq(users.id, id) }),
  ['user'],
  { revalidate: 60, tags: ['user'] }
)

// Invalidate on mutation
export async function updateUserAction(id: string, data: Partial<User>) {
  await db.update(users).set(data).where(eq(users.id, id))
  revalidateTag('user')
  await redis.del(`user:${id}`)
}
```

### Queue / Background Jobs Pattern

```ts
// lib/queue/workers/email.worker.ts
import { Queue, Worker } from 'bullmq'
import { connection } from '@/lib/redis'

export const emailQueue = new Queue('emails', { connection })

type EmailJob = {
  to: string
  subject: string
  template: 'welcome' | 'reset-password' | 'invite'
  data: Record<string, string>
}

export const emailWorker = new Worker<EmailJob>(
  'emails',
  async (job) => {
    const { to, subject, template, data } = job.data
    await sendEmail({ to, subject, html: renderTemplate(template, data) })
  },
  { connection, concurrency: 10 }
)

emailWorker.on('failed', (job, err) => {
  console.error(`Email job ${job?.id} failed:`, err)
})
```

### API Design Principles

```ts
// Always version your API
// /api/v1/users

// Consistent response envelope
type ApiSuccess<T> = { data: T; meta?: { total: number; page: number } }
type ApiError = { error: { code: string; message: string; details?: unknown } }

// Paginated list endpoint pattern
export async function GET(req: NextRequest) {
  const { searchParams } = req.nextUrl
  const page = Math.max(1, Number(searchParams.get('page') ?? 1))
  const limit = Math.min(100, Math.max(1, Number(searchParams.get('limit') ?? 20)))
  const offset = (page - 1) * limit

  const [items, total] = await Promise.all([
    db.select().from(users).limit(limit).offset(offset),
    db.select({ count: count() }).from(users),
  ])

  return NextResponse.json({
    data: items,
    meta: { total: total[0].count, page, limit },
  })
}
```

---

## 4. Debug, Refactor & Code Review

### Debug Protocol

When diagnosing a bug, always follow this sequence:

1. **Reproduce** — Confirm the exact input that triggers the issue
2. **Isolate** — Binary search the call stack: which layer (UI/API/DB) breaks first?
3. **Hypothesize** — Form exactly ONE hypothesis before reading code
4. **Verify** — Add a targeted log/test to confirm or deny
5. **Fix** — Change the minimum code needed to fix the root cause
6. **Prevent** — Add a test that would have caught this

```ts
// Debugging async/concurrent issues
// Add correlation IDs to trace requests through the stack
import { AsyncLocalStorage } from 'async_hooks'

const requestContext = new AsyncLocalStorage<{ requestId: string }>()

export function withRequestId<T>(fn: () => T): T {
  return requestContext.run({ requestId: crypto.randomUUID() }, fn)
}

export function getRequestId() {
  return requestContext.getStore()?.requestId ?? 'unknown'
}

// Structured logging — always include context
export const logger = {
  info: (msg: string, ctx?: Record<string, unknown>) =>
    console.log(JSON.stringify({ level: 'info', msg, requestId: getRequestId(), ...ctx })),
  error: (msg: string, err: unknown, ctx?: Record<string, unknown>) =>
    console.error(JSON.stringify({ level: 'error', msg, error: String(err), requestId: getRequestId(), ...ctx })),
}
```

### Refactoring Checklist

Before refactoring any code, verify:

- [ ] Tests exist for the code being changed (write them first if not)
- [ ] Understand WHY the code was written the way it was — check git blame
- [ ] Refactor in small, independently reviewable commits
- [ ] No behaviour changes — only structure changes

**Patterns to eliminate:**
```ts
// ❌ Deeply nested callbacks / promise chains
getUserById(id, (err, user) => {
  if (err) return handleError(err)
  getOrgById(user.orgId, (err, org) => { ... })
})

// ✅ Async/await with proper error handling
const user = await getUserById(id)
const org = await getOrgById(user.orgId)

// ❌ Any type spreading
const result: any = await fetch('/api').then(r => r.json())

// ✅ Typed and validated
const raw = await fetch('/api').then(r => r.json())
const result = ResponseSchema.parse(raw)

// ❌ Boolean flag parameters
renderUser(user, true, false, true)

// ✅ Options object
renderUser(user, { showAvatar: true, compact: false, showEmail: true })

// ❌ Magic strings
if (user.status === 'active') { ... }

// ✅ Const enum or as const
const USER_STATUS = { ACTIVE: 'active', INACTIVE: 'inactive' } as const
type UserStatus = typeof USER_STATUS[keyof typeof USER_STATUS]
if (user.status === USER_STATUS.ACTIVE) { ... }

// ❌ Mutation inside map/filter
const results = items.map(item => { item.processed = true; return item })

// ✅ Pure transformations
const results = items.map(item => ({ ...item, processed: true }))
```

### Code Review Standards

Every PR must be reviewed against these dimensions:

**Correctness**
- Does it handle all edge cases (empty arrays, null values, concurrent mutations)?
- Are all error paths handled and returning the correct status codes?
- Are database transactions used where multiple writes must be atomic?

**Security**
- Is all user input validated with Zod before use?
- No secrets or sensitive data in logs
- SQL injection impossible (parameterized queries via Drizzle)
- Auth checked on every protected route/action
- Rate limiting on public endpoints

**Performance**
- No N+1 queries (use `.with()` in Drizzle for relations)
- Heavy operations pushed to background queue
- Large lists paginated
- Images optimized via `next/image`

**Maintainability**
- Functions do one thing (< 30 lines is a good signal)
- No magic numbers — extract as named constants
- Types flow through the system — no casting at every layer

---

## 5. Quality Checklist

Before delivering any code:

**TypeScript**
- [ ] Zero `any` types
- [ ] All external data validated with Zod
- [ ] Env vars validated at startup
- [ ] Explicit return types on all exported functions

**Next.js**
- [ ] Server Components used by default, Client Components only where needed
- [ ] Server Actions used for mutations (not separate API routes for internal calls)
- [ ] `revalidatePath` / `revalidateTag` called after every mutation
- [ ] `loading.tsx` and `error.tsx` provided for all route segments

**API**
- [ ] Every route handler has auth check
- [ ] Input validated before DB access
- [ ] Consistent error response shape
- [ ] HTTP status codes correct (201 for create, 204 for delete, 400 for validation, 401 for unauth, 403 for forbidden, 404 for not found)

**Database**
- [ ] Migrations written and reversible
- [ ] Indexes on all FK columns and frequently filtered columns
- [ ] Transactions used for multi-step writes
- [ ] No raw SQL unless Drizzle cannot express it

**AI / Agents**
- [ ] Model, temperature, and max_tokens explicitly set
- [ ] Structured output used where structured data is expected
- [ ] Prompt versioned and stored (not inline strings)
- [ ] Token usage logged for cost monitoring
- [ ] Fallback model defined

**Security**
- [ ] Auth on every protected endpoint
- [ ] All user input validated and sanitised
- [ ] Rate limiting on public endpoints
- [ ] No sensitive data in client-side bundles

---

Remember: Superpowers come from discipline, not shortcuts. Write code that your future self — and your teammates — will be grateful for.
