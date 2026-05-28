import { NextResponse } from "next/server";
import { getFastApiBaseUrl, getFastApiTenantId } from "@/lib/fastapi-backend";

/**
 * Proxy endpoint for listing available TTS voices.
 * Forwards requests to the FastAPI backend /voice/voices endpoint.
 */
export async function GET(request) {
  const { searchParams } = new URL(request.url);
  const ttsProvider = searchParams.get("tts_provider") || "elevenlabs";
  const language = searchParams.get("language");

  const baseUrl = getFastApiBaseUrl();
  let url = `${baseUrl}/voice/voices?tts_provider=${encodeURIComponent(ttsProvider)}`;
  if (language) {
    url += `&language=${encodeURIComponent(language)}`;
  }

  try {
    const response = await fetch(url, {
      method: "GET",
      headers: {
        "Content-Type": "application/json",
        "X-Tenant-Id": getFastApiTenantId(),
      },
    });

    if (!response.ok) {
      const errorText = await response.text().catch(() => "");
      return NextResponse.json(
        { error: errorText || "Failed to fetch voices", voices: [] },
        { status: response.status }
      );
    }

    const data = await response.json();
    
    // Ensure we return an array of voices
    const voices = Array.isArray(data) ? data : (data.voices || []);
    
    return NextResponse.json({ voices });
  } catch (error) {
    return NextResponse.json(
      {
        error: "Voice service is unreachable.",
        detail: String(error?.message || error),
        voices: [],
      },
      { status: 502 }
    );
  }
}
