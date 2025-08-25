# api.py
import json
import subprocess
from typing import Any, Dict, List, Optional
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

app = FastAPI(title="RO → DE translator (Reverso)")

class TranslateRequest(BaseModel):
    word: str  # Romanian input

class TranslateResponse(BaseModel):
    input: str
    output_language: str
    output_word: str
    source_language: str = "romanian"
    strategy: str  # "translation" or "context"
    details: Dict[str, Any]

def call_reverso(text: str, source: str, target: str, mode: str = "translation") -> dict:
    try:
        proc = subprocess.run(
            ["node", "reverso_helper.js"],
            input=json.dumps({"text": text, "from": source, "to": target, "mode": mode}),
            capture_output=True,
            text=True,
            check=True,
        )
        return json.loads(proc.stdout)
    except subprocess.CalledProcessError as e:
        try:
            return json.loads(e.stderr)
        except Exception:
            return {"ok": False, "message": e.stderr.strip() or "Unknown error"}
    except FileNotFoundError:
        return {"ok": False, "message": "Node.js not found. Ensure 'node' is on PATH."}

def pick_top_from_translation(payload: dict) -> Optional[str]:
    """Try common shapes returned by getTranslation."""
    res = payload.get("result") if "result" in payload else payload
    if not isinstance(res, dict):
        return None
    for k in ("translation", "translations", "result", "results"):
        val = res.get(k)
        if isinstance(val, list) and val:
            first = val[0]
            if isinstance(first, str):
                return first
            if isinstance(first, dict):
                for kk in ("translation", "text", "value"):
                    if isinstance(first.get(kk), str):
                        return first[kk]
    return None

def pick_top_from_context(payload: dict) -> Optional[str]:
    """Heuristics for getContext result: scan for a list of candidate translations."""
    res = payload.get("result") if "result" in payload else payload
    if not isinstance(res, dict):
        return None

    # Common fields to try (varies across versions)
    candidates: List[Any] = []
    for k in (
        "translation", "translations",               # flat arrays
        "results", "examples", "contextResults",     # nested places
    ):
        v = res.get(k)
        if isinstance(v, list):
            candidates.extend(v)
        elif isinstance(v, dict):
            # e.g., { translation: [...] }
            for kk in ("translation", "translations"):
                if isinstance(v.get(kk), list):
                    candidates.extend(v[kk])

    # Pull the first meaningful string from the candidates
    for item in candidates:
        if isinstance(item, str) and item.strip():
            return item.strip()
        if isinstance(item, dict):
            for kk in ("translation", "text", "value", "to"):
                if isinstance(item.get(kk), str) and item[kk].strip():
                    return item[kk].strip()
    return None

@app.post("/translate-ro-de", response_model=TranslateResponse)
def translate_ro_de(req: TranslateRequest):
    src = "romanian"
    tgt = "german"

    # Try direct translation first
    t1 = call_reverso(req.word, src, tgt, mode="translation")
    if t1.get("ok"):
        out = pick_top_from_translation(t1)
        if out:
            return TranslateResponse(
                input=req.word,
                output_language=tgt,
                output_word=out,
                strategy="translation",
                details={"ro_de_raw": t1},
            )

    # Fallback to context
    t2 = call_reverso(req.word, src, tgt, mode="context")
    if not t2.get("ok"):
        raise HTTPException(status_code=502, detail=f"RO→DE failed: {t2.get('message','Unknown error')}")

    out2 = pick_top_from_context(t2)
    if not out2:
        raise HTTPException(status_code=502, detail="RO→DE returned no usable German candidate (context).")

    return TranslateResponse(
        input=req.word,
        output_language=tgt,
        output_word=out2,
        strategy="context",
        details={"ro_de_raw": t2},
    )
