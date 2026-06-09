import { NextRequest, NextResponse } from "next/server";

export async function GET(request: NextRequest) {
  const searchParams = request.nextUrl.searchParams;
  const code = searchParams.get("code");
  const state = searchParams.get("state");

  if (!code) {
    return NextResponse.redirect(new URL("/login?error=no_code", request.url));
  }

  try {
    const backendUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
    
    const response = await fetch(
      `${backendUrl}/api/v1/auth/callback/google?code=${code}&state=${state}`,
      { method: "GET" }
    );

    if (response.ok) {
      const setCookie = response.headers.get("set-cookie");
      const redirectResponse = NextResponse.redirect(
        new URL("/", request.url)
      );
      if (setCookie) {
        redirectResponse.headers.set("set-cookie", setCookie);
      }
      return redirectResponse;
    }

    return NextResponse.redirect(new URL("/login?error=auth_failed", request.url));
  } catch {
    return NextResponse.redirect(new URL("/login?error=server_error", request.url));
  }
}