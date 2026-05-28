"""Tiny HTML prompt UI that POSTs to /chat on the same service."""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.responses import HTMLResponse


def register_playground(app: FastAPI, title: str) -> None:
    page = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8"/><meta name="viewport" content="width=device-width, initial-scale=1"/>
<title>__TITLE__</title>
<style>
body{font-family:system-ui,sans-serif;margin:1.25rem;max-width:52rem;}
label{font-weight:600;display:block;margin-top:.5rem;}
textarea{width:100%;min-height:7rem;margin:.35rem 0 1rem;padding:.5rem;box-sizing:border-box;}
button{padding:.55rem 1.1rem;cursor:pointer;}
#out{margin-top:1rem;padding:.75rem;background:#f4f4f5;border-radius:6px;white-space:pre-wrap;word-break:break-word;}
.err{color:#b91c1c;}
.hint{font-size:.875rem;color:#71717a;}
</style></head>
<body>
<h1>__TITLE__</h1>
<p class="hint">Tests <code>POST /chat</code> with <code>{{"query": "..."}}</code>. Configure LLM keys in <code>.env</code>.</p>
<label for="q">Prompt</label>
<textarea id="q" placeholder="Ask something in this bot&#39;s topic"></textarea>
<button type="button" id="send">Send</button>
<div id="out"></div>
<script>
const q=document.getElementById("q"),out=document.getElementById("out");
document.getElementById("send").onclick=async()=>{
  out.textContent="Waiting…";out.classList.remove("err");
  try{
    const r=await fetch("/chat",{method:"POST",headers:{"Content-Type":"application/json"},
      body:JSON.stringify({query:q.value})});
    const t=await r.text();
    let j;try{j=JSON.parse(t)}catch(_){}
    out.textContent=r.ok?(j?JSON.stringify(j,null,2):t):("HTTP "+r.status+"\\n\\n"+t);
    if(!r.ok)out.classList.add("err");
  }catch(e){out.textContent=String(e);out.classList.add("err");}
};
</script></body></html>""".replace(
        "__TITLE__", title.replace("<", "").replace(">", "")
    )

    @app.get("/playground", response_class=HTMLResponse)
    async def _playground() -> HTMLResponse:
        return HTMLResponse(page)
