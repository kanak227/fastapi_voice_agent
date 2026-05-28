// app/api/EduthumChat/route.js

import { NextResponse } from "next/server";
import {
  EDUCATION_FALLBACK,
  isEducationTopicAllowedByIntent,
} from "@/lib/domain-guardrails";
import { createParser } from "../../eventsource-parser.js";
import {
  attachAgentDomainPayloadField,
  getFastApiBaseUrl,
  getFastApiTenantIdForAgentDomain,
} from "@/lib/fastapi-backend";

const DOMAIN_SLUG = "education";

export async function POST(request) {
  try {
    const body = await request.json();
    const { query, session_id, history, language } = body;
    const normalizedQuery = String(query || "").trim();
    const sid = session_id || `education-${Date.now()}`;
    const lang = language || "en-US";

    if (!normalizedQuery) {
      return NextResponse.json(
        { response: "Please provide a valid query." },
        { status: 400 }
      );
    }

    if (!isEducationTopicAllowedByIntent(normalizedQuery)) {
      return NextResponse.json({ response: EDUCATION_FALLBACK });
    }

    const baseUrl = getFastApiBaseUrl();
    const chatUrl = `${baseUrl}/agent/stream`;

    const response = await fetch(chatUrl, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-Tenant-Id": getFastApiTenantIdForAgentDomain(DOMAIN_SLUG),
      },
      body: JSON.stringify(
        attachAgentDomainPayloadField(
          {
            session_id: sid,
            input_type: "text",
            text: normalizedQuery,
            domain: DOMAIN_SLUG,
            language: lang,
            output_audio: false,
            use_knowledge: true,
            knowledge_top_k: 3,
            history: history || [],
          },
          DOMAIN_SLUG
        )
      ),
    });

    if (!response.ok) {
      const errorText = await response.text();
      throw new Error(
        `Chat API failed: ${response.status} - ${errorText || response.statusText}`
      );
    }

    // --- STREAM SSE ---
    let finalText = "";
    let tokenText = "";
    let doneOk = true;
    let failReason = "";
    const decoder = new TextDecoder();
    const parser = createParser((event) => {
      if (event.type === "event") {
        if (event.event === "final_text") {
          try {
            const data = JSON.parse(event.data);
            finalText = typeof data === "string" ? data : String(data?.text || "");
          } catch {
            finalText = event.data;
          }
        }
        if (event.event === "text") {
          try {
            const data = JSON.parse(event.data);
            tokenText += typeof data === "string" ? data : String(data?.text || "");
          } catch {
            tokenText += event.data;
          }
        }
        if (event.event === "done") {
          try {
            const data = JSON.parse(event.data);
            doneOk = data.ok !== false;
            failReason = String(data.reason || "");
          } catch {
            doneOk = true;
          }
        }
      }
    });

    if (!response.body) {
      return NextResponse.json({ response: "No response body from upstream." }, { status: 502 });
    }
    for await (const chunk of response.body) {
      parser.feed(decoder.decode(chunk));
    }
    parser.flush();

    if (!doneOk) {
      return NextResponse.json(
        { response: failReason || "AI service failed to complete the response." },
        { status: 502 }
      );
    }

    const responseText = String(finalText || tokenText || "").trim();

    return NextResponse.json({
      response: responseText || "No response received from the AI service.",
    });
  } catch (error) {
    console.error("Chat API error:", error);
    return NextResponse.json(
      { response: "Sorry, there was an error processing your query." },
      { status: 500 }
    );
  }
}

export async function GET() {
  return NextResponse.json({
    message: "Eduthum Chat API - Use POST with { query } in JSON body",
  });
}
