import { NextResponse } from "next/server";
import { getFastApiBaseUrl, getFastApiTenantId } from "@/lib/fastapi-backend";

export const dynamic = "force-dynamic";

export async function GET(request) {
  const { searchParams } = new URL(request.url);
  const ttsProvider = searchParams.get("tts_provider") || "elevenlabs";
  const language = searchParams.get("language") || "";

  const baseUrl = getFastApiBaseUrl();
  const apiUrl = `${baseUrl}/voice/voices?tts_provider=${encodeURIComponent(ttsProvider)}${language ? `&language=${encodeURIComponent(language)}` : ""}`;

  try {
    const upstream = await fetch(apiUrl, {
      method: "GET",
      headers: { "X-Tenant-Id": getFastApiTenantId() },
      cache: "no-store",
    });
    if (!upstream.ok) {
      return NextResponse.json({ voices: [] }, { status: 200 });
    }
    const data = await upstream.json().catch(() => []);
    return NextResponse.json({ voices: Array.isArray(data) ? data : [] });
  } catch {
    return NextResponse.json({ voices: [] }, { status: 200 });
  }
}
