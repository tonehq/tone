// The `disposable-email-domains` package ships a JSON array without type
// declarations. This ambient module lets TypeScript strict mode compile the
// default import used by `src/lib/emailDomain.ts`.
declare module 'disposable-email-domains' {
  const domains: readonly string[];
  export default domains;
}
