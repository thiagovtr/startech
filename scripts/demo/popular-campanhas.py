#!/usr/bin/env python3
"""Popula campanhas variadas de teste pelo fluxo real (Gateway -> BFF Web -> CQRS)."""
import datetime
import json
import os
import urllib.parse
import urllib.request

GW = f"http://localhost:{os.environ.get('GATEWAY_HOST_PORT', '8080')}"
KC = f"http://localhost:{os.environ.get('KEYCLOAK_HOST_PORT', '8089')}"

CAMPANHAS = [
    ("Urgência tipo A+ — Lavras", "Hemominas Lavras", "A+", "CRITICO"),
    ("Reforço estoque O+", "Hemocentro Regional de Varginha", "O+", "NORMAL"),
    ("Mutirão de Doação B+", "Santa Casa de Lavras", "B+", "NORMAL"),
    ("Alerta estoque AB-", "Hemominas Pouso Alegre", "AB-", "CRITICO"),
    ("Campanha Solidária A-", "Hemominas Lavras", "A-", "NORMAL"),
]


def main() -> None:
    form = urllib.parse.urlencode({
        "grant_type": "password",
        "client_id": "startech-web",
        "username": "operador1@startech.local",
        "password": "operador123",
    }).encode()
    tok_url = f"{KC}/realms/startech/protocol/openid-connect/token"
    token = json.loads(urllib.request.urlopen(tok_url, form, timeout=15).read())["access_token"]

    hoje = str(datetime.date.today())
    fim = str(datetime.date.today() + datetime.timedelta(days=45))
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

    for titulo, hemocentro, tipo, urgencia in CAMPANHAS:
        payload = {
            "titulo": titulo,
            "hemocentro": hemocentro,
            "tipo_sanguineo": tipo,
            "urgencia": urgencia,
            "data_inicio": hoje,
            "data_fim": fim,
        }
        req = urllib.request.Request(f"{GW}/api/web/campanhas", json.dumps(payload).encode(), headers)
        criada = json.loads(urllib.request.urlopen(req, timeout=15).read())
        print(f"[OK] {criada['id']} | {criada['tipo_sanguineo']} | {criada['titulo']}")


if __name__ == "__main__":
    main()
