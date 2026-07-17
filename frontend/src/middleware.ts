import { NextRequest, NextResponse } from 'next/server';

import { ACCESS_TOKEN, ROUTE_HOME, ROUTE_LOGIN } from '@/constants';

// Public (unauthenticated) pages under the (auth) route group, plus the root
// redirector. Everything else requires a session cookie.
const PUBLIC_PATHS = [
  ROUTE_LOGIN,
  '/signup',
  '/sign-in-with-code',
  '/accept-invite',
  '/forgot-password',
  '/reset-password',
  '/verify-email',
];

function isPublicPath(pathname: string): boolean {
  if (pathname === '/') return true;
  return PUBLIC_PATHS.some((p) => pathname === p || pathname.startsWith(`${p}/`));
}

/**
 * Server-side auth guard. The access JWT lives in an httpOnly cookie scoped to
 * the shared parent domain, so it reaches this Next.js origin and can be read
 * here (JS in the browser cannot). We gate on cookie *presence*; validity is
 * enforced per-request by the API (401 → silent refresh). The cookie outlives
 * the short JWT (session-length max-age) so this check stays true across
 * silent refreshes.
 */
export function middleware(request: NextRequest) {
  const { pathname, search } = request.nextUrl;
  const hasSession = request.cookies.has(ACCESS_TOKEN);

  if (isPublicPath(pathname)) {
    // Already-authenticated users shouldn't sit on the login page.
    if (hasSession && pathname === ROUTE_LOGIN) {
      return NextResponse.redirect(new URL(ROUTE_HOME, request.url));
    }
    return NextResponse.next();
  }

  if (!hasSession) {
    const loginUrl = new URL(ROUTE_LOGIN, request.url);
    const returnTo = `${pathname}${search}`;
    if (returnTo && returnTo !== '/') {
      loginUrl.searchParams.set('next', returnTo);
    }
    return NextResponse.redirect(loginUrl);
  }

  return NextResponse.next();
}

export const config = {
  // Run on every route except API (incl. the dev proxy), Next internals, and
  // static files (any path with a file extension, e.g. .png/.css/.ico).
  matcher: ['/((?!api|_next/static|_next/image|favicon.ico|.*\\..*).*)'],
};
