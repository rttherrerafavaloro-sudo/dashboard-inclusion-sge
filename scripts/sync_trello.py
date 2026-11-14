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
    "objetivos", "objetivo 2026", "objetivo 2026:", "tareas",
    "tareas 2026", "reuniones", "reuniones generales",
    "desbloqueo y reparaciones", "sge", "conectar tecnico",
    "en proceso"
}

def normalize_title(value):
    value = clean_text(value).casefold()
    value = value.replace("á", "a").replace("é", "e").replace("í", "i")
    value = value.replace("ó", "o").replace("ú", "u").replace("ü", "u")
    return re.sub(r"[^a-z0-9]+", " ", value).strip()
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


    # Exclude section-heading cards regardless of accents or punctuation.
    # Archived task cards remain in the historical total, as before.
    normalized_headers = {normalize_title(x) for x in HEADER_CARDS}
    real_cards = [
        c for c in cards
        if normalize_title(c.get("name")) not in normalized_headers
    ]

    complete = [c for c in real_cards if c.get("dueComplete")]
    pending = [c for c in real_cards if not c.get("dueComplete") and not c.get("closed")]
    by_area = Counter(list_names.get(c.get("idList"), "Otra") for c in real_cards)
    complete_by_area = Counter(list_names.get(c.get("idList"), "Otra") for c in complete)
    pending_by_area = Counter(list_names.get(c.get("idList"), "Otra") for c in pending)

    created_dates = {}
    for action in activities:
        if action.get("type") == "createCard":
            card = (action.get("data") or {}).get("card") or {}
            if card.get("id"):
                created_dates[card["id"]] = action.get("date")

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
            "createdAt": created_dates.get(c["id"]),
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
    public_cards_by_id = {c["id"]: c for c in public_cards}
    # Una sola entrada por tarjeta: conservar el movimiento más reciente.
    latest_by_card = {}
    for action in activities:
        data = action.get("data") or {}
        card = data.get("card") or {}
        card_id = card.get("id")
        if card_id not in public_ids:
            continue
        action_date = action.get("date") or ""
        if card_id in latest_by_card and (latest_by_card[card_id].get("date") or "") >= action_date:
            continue
        current_card = public_cards_by_id[card_id]
        item = {
            "cardId": card_id,
            "date": action_date,
            "type": action.get("type"),
            "cardTitle": current_card["title"],
            "area": current_card["area"],
        }
        # Only expose list transitions, never comment text or member identities.
        if action.get("type") == "updateCard":
            before = data.get("listBefore") or {}
            after = data.get("listAfter") or {}
            if before.get("name") or after.get("name"):
                item["fromList"] = before.get("name")
                item["toList"] = after.get("name")
        latest_by_card[card_id] = item
    timeline = sorted(latest_by_card.values(), key=lambda x: x.get("date") or "", reverse=True)

    snapshot = {
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "boardUrl": "https://trello.com/b/6Ve8yJxP/inclusi%C3%B3n-tecnol%C3%B3gica-sge",
        "metrics": {
            "total": len(real_cards),
            "completed": len(complete),
            "pending": len(pending),
            "percent": round(100 * len(complete) / len(real_cards)) if real_cards else 0,
            "byArea": dict(sorted(by_area.items())),
            "completedByArea": dict(sorted(complete_by_area.items())),
            "pendingByArea": dict(sorted(pending_by_area.items()))
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
