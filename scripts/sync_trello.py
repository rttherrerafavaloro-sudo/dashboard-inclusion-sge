#!/usr/bin/env python3
"""Build a privacy-filtered public Trello snapshot for GitHub Pages.

Only cards explicitly labeled PUBLICAR appear by title in the public catalog/history.
Descriptions require PUBLICAR-DETALLE. Image attachments require PUBLICAR-IMAGENES.
Never publish comments, member names, emails, or raw Trello action payloads.
"""
import json
import os
import re
import urllib.parse
import urllib.request
from collections import Counter
from datetime import datetime, timezone

API_KEY = os.environ["TRELLO_KEY"]
API_TOKEN = os.environ["TRELLO_TOKEN"]
BOARD_ID = "6Ve8yJxP"
BASE = "https://api.trello.com/1"
HEADERS = {"User-Agent": "CFP-SGE-Dashboard/1.0"}
HEADER_CARDS = {
    "objetivos", "objetivo 2026:", "tareas", "reuniones",
    "desbloqueo y reparaciones", "sge"
}
PUBLIC_LABEL = "PUBLICAR"
DETAIL_LABEL = "PUBLICAR-DETALLE"
IMAGE_LABEL = "PUBLICAR-IMAGENES"

def api(path, params=None):
    params = dict(params or {})
    params.update({"key": API_KEY, "token": API_TOKEN})
    url = BASE + path + "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=40) as response:
        return json.loads(response.read().decode("utf-8"))

def clean_text(value, limit=6000):
    value = (value or "").strip()
    value = re.sub(r"\x00", "", value)
    return value[:limit]

def main():
    cards = api(f"/boards/{BOARD_ID}/cards", {
        "filter": "all",
        "fields": "id,name,desc,url,idList,due,dueComplete,dateLastActivity,closed,labels",
        "attachments": "true",
        "attachment_fields": "id,name,url,mimeType,previews"
    })
    lists = api(f"/boards/{BOARD_ID}/lists", {"filter": "all", "fields": "id,name,closed"})
    list_names = {item["id"]: item["name"] for item in lists}
    activities = api(f"/boards/{BOARD_ID}/actions", {
        "limit": "1000",
        "filter": "createCard,updateCard,addAttachmentToCard,updateCheckItemStateOnCard",
        "fields": "id,date,type,data"
    })

    activities_cards = {}
    for action in activities:
        data = action.get("data") or {}
        card = data.get("card") or {}
        if card.get("id"):
            activities_cards[card["id"]] = card.get("name", "")

    real_cards = [
        c for c in cards
        if clean_text(c.get("name")).casefold() not in HEADER_CARDS
        and not c.get("closed", False)
    ]
    # Keep closed section-header cards out, but count archived/closed task cards
    # only if they are not one of the exact heading cards.
    real_cards = [
        c for c in cards
        if clean_text(c.get("name")).casefold() not in HEADER_CARDS
    ]

    complete = [c for c in real_cards if c.get("dueComplete")]
    pending = [c for c in real_cards if not c.get("dueComplete") and not c.get("closed")]
    by_area = Counter(list_names.get(c.get("idList"), "Otra") for c in real_cards)

    public_cards = []
    for c in real_cards:
        labels = {clean_text(label.get("name")).upper() for label in c.get("labels", [])}
        if PUBLIC_LABEL not in labels:
            continue
        item = {
            "id": c["id"],
            "title": clean_text(c.get("name"), 240),
            "url": c.get("url", ""),
            "area": list_names.get(c.get("idList"), "Otra"),
            "completed": bool(c.get("dueComplete")),
            "closed": bool(c.get("closed")),
            "due": c.get("due"),
            "lastActivity": c.get("dateLastActivity"),
        }
        if DETAIL_LABEL in labels:
            item["description"] = clean_text(c.get("desc"), 4000)
        if IMAGE_LABEL in labels:
            images = []
            for attachment in c.get("attachments", []):
                mime = (attachment.get("mimeType") or "").lower()
                if mime.startswith("image/") and attachment.get("url"):
                    images.append({
                        "name": clean_text(attachment.get("name"), 160),
                        "url": attachment["url"],
                        "mimeType": mime
                    })
            item["images"] = images[:4]
        public_cards.append(item)

    public_ids = {c["id"] for c in public_cards}
    timeline = []
    for action in activities:
        data = action.get("data") or {}
        card = data.get("card") or {}
        if card.get("id") not in public_ids:
            continue
        item = {
            "date": action.get("date"),
            "type": action.get("type"),
            "cardTitle": clean_text(card.get("name"), 240),
        }
        # Only expose list transitions, never comment text or member identities.
        if action.get("type") == "updateCard":
            before = data.get("listBefore") or {}
            after = data.get("listAfter") or {}
            if before.get("name") or after.get("name"):
                item["fromList"] = before.get("name")
                item["toList"] = after.get("name")
        timeline.append(item)
    timeline.sort(key=lambda x: x.get("date") or "", reverse=True)

    snapshot = {
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "boardUrl": "https://trello.com/b/6Ve8yJxP/inclusi%C3%B3n-tecnol%C3%B3gica-sge",
        "metrics": {
            "total": len(real_cards),
            "completed": len(complete),
            "pending": len(pending),
            "percent": round(100 * len(complete) / len(real_cards)) if real_cards else 0,
            "byArea": dict(sorted(by_area.items()))
        },
        "publicCards": public_cards,
        "timeline": timeline[:100],
        "privacy": {
            "publicCardCount": len(public_cards),
            "rules": "Solo se publican tarjetas con etiqueta PUBLICAR. Descripciones e imágenes requieren etiquetas adicionales. Comentarios y nombres de integrantes nunca se publican."
        }
    }
    os.makedirs("data", exist_ok=True)
    with open("data/trello.json", "w", encoding="utf-8") as f:
        json.dump(snapshot, f, ensure_ascii=False, indent=2)
        f.write("\n")
    print("Snapshot generado:", snapshot["metrics"]["total"], "actividades;",
          len(public_cards), "tarjetas autorizadas para publicación.")

if __name__ == "__main__":
    main()
