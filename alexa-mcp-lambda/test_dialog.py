#!/usr/bin/env python3
"""
Verifica locale del flusso a più turni della skill (nota sulla spesa).

Non è pytest (il progetto non lo usa, vedi pyspendless/test/test_task23_0.py):
è uno script con controlli espliciti. Fa girare `lambda_function.handler` su
envelope Alexa costruite a mano, con `requests.post` sostituito da un finto
server MCP: nessuna chiamata di rete, nessun token vero, nessun movimento
registrato davvero.

Gli attributi di sessione vengono riportati da un turno al successivo esattamente
come fa Alexa, perché è lì che vive il movimento in attesa della nota.

Uso:
    .venv/bin/python test_dialog.py
"""

import json
import sys

import lambda_function

SKILL_ID = "amzn1.ask.skill.test"
ACCESS_TOKEN = "token-di-prova"

chiamate = []


class _FintaRisposta:
    status_code = 200

    def raise_for_status(self):
        return None

    def json(self):
        return {
            "jsonrpc": "2.0",
            "id": 1,
            "result": {
                "content": [{"type": "text", "text": "Registrato."}],
                "isError": False,
            },
        }


def _finta_post(url, headers=None, json=None, timeout=None):
    chiamate.append(json["params"])
    return _FintaRisposta()


lambda_function.requests.post = _finta_post


def envelope(request, session_attributes=None, access_token=ACCESS_TOKEN):
    user = {"userId": "amzn1.ask.account.test"}
    if access_token:
        user["accessToken"] = access_token
    return {
        "version": "1.0",
        "session": {
            "new": False,
            "sessionId": "amzn1.echo-api.session.test",
            "application": {"applicationId": SKILL_ID},
            "user": user,
            "attributes": session_attributes or {},
        },
        "context": {
            "System": {
                "application": {"applicationId": SKILL_ID},
                "user": user,
                "device": {"deviceId": "dev1", "supportedInterfaces": {}},
                "apiEndpoint": "https://api.eu.amazonalexa.com",
            }
        },
        "request": request,
    }


def intent_request(name, slots=None, request_type="IntentRequest"):
    return {
        "type": request_type,
        "requestId": "amzn1.echo-api.request.test",
        "timestamp": "2026-10-20T10:00:00Z",
        "locale": "it-IT",
        "intent": {
            "name": name,
            "confirmationStatus": "NONE",
            "slots": {
                nome: {"name": nome, "value": valore, "confirmationStatus": "NONE"}
                for nome, valore in (slots or {}).items()
            },
        },
    }


def parla(risposta):
    speech = (risposta.get("response") or {}).get("outputSpeech") or {}
    return speech.get("ssml", "")


def direttive(risposta):
    return (risposta.get("response") or {}).get("directives") or []


def attributi(risposta):
    return risposta.get("sessionAttributes") or {}


class Verifica:
    def __init__(self):
        self.ok = 0
        self.ko = 0

    def check(self, descrizione, condizione, dettaglio=None):
        if condizione:
            self.ok += 1
            print("  OK   {}".format(descrizione))
        else:
            self.ko += 1
            print("  FAIL {}{}".format(descrizione, "" if dettaglio is None else "  <- {}".format(dettaglio)))


def main():
    v = Verifica()

    print("\n1. Primo turno: chiede la nota e non registra niente")
    chiamate.clear()
    r1 = lambda_function.handler(
        envelope(intent_request("AddMovementIntent", {"amount": "20", "category": "spesa alimentare"})), None
    )
    v.check("nessuna chiamata al server nel primo turno", not chiamate, chiamate)
    v.check("chiede se aggiungere una nota", "Vuoi aggiungere una nota?" in parla(r1), parla(r1))
    v.check("riepiloga importo e categoria", "20 euro per spesa alimentare" in parla(r1), parla(r1))
    pending = attributi(r1).get("pending_movement")
    v.check("movimento messo in attesa negli attributi di sessione", pending is not None, attributi(r1))
    v.check("il movimento in attesa non ha nota", pending and "note" not in pending, pending)
    sessione = attributi(r1)

    print("\n2. «Sì» -> elicitazione dello slot note")
    chiamate.clear()
    r2 = lambda_function.handler(envelope(intent_request("AMAZON.YesIntent"), sessione), None)
    d = direttive(r2)
    v.check("nessuna chiamata al server", not chiamate, chiamate)
    v.check("una direttiva Dialog.ElicitSlot", len(d) == 1 and d[0]["type"] == "Dialog.ElicitSlot", d)
    v.check("elicita proprio lo slot 'note'", d and d[0].get("slotToElicit") == "note", d)
    v.check("updatedIntent è AddMovementIntent", d and d[0]["updatedIntent"]["name"] == "AddMovementIntent", d)
    slot_rimandati = d[0]["updatedIntent"]["slots"] if d else {}
    v.check(
        "importo e categoria già riempiti, così non li richiede",
        slot_rimandati.get("amount", {}).get("value") == "20"
        and slot_rimandati.get("category", {}).get("value") == "spesa alimentare",
        slot_rimandati,
    )
    v.check("il movimento resta in attesa", attributi(r2).get("pending_movement") is not None, attributi(r2))
    sessione = attributi(r2)

    print("\n3. La nota detta a voce finisce in add_movement")
    chiamate.clear()
    r3 = lambda_function.handler(
        envelope(
            intent_request(
                "AddMovementIntent",
                {"amount": "20", "category": "spesa alimentare", "note": "cena fuori con i nonni"},
            ),
            sessione,
        ),
        None,
    )
    v.check("una sola chiamata add_movement", len(chiamate) == 1 and chiamate[0]["name"] == "add_movement", chiamate)
    argomenti = chiamate[0]["arguments"] if chiamate else {}
    v.check("la nota è nel payload", argomenti.get("note") == "cena fuori con i nonni", argomenti)
    v.check("importo e categoria conservati", argomenti.get("amount") == "20"
            and argomenti.get("category") == "spesa alimentare", argomenti)
    v.check("il movimento in attesa è stato consumato", "pending_movement" not in attributi(r3), attributi(r3))
    v.check("riporta la risposta del server", "Registrato." in parla(r3), parla(r3))

    print("\n4. «No» -> registra senza nota")
    chiamate.clear()
    r4 = lambda_function.handler(
        envelope(intent_request("AddMovementIntent", {"amount": "15", "category": "trasporti"})), None
    )
    r4 = lambda_function.handler(envelope(intent_request("AMAZON.NoIntent"), attributi(r4)), None)
    v.check("add_movement chiamato una volta", len(chiamate) == 1, chiamate)
    v.check("nessuna nota nel payload", chiamate and "note" not in chiamate[0]["arguments"], chiamate)
    v.check("attesa consumata", "pending_movement" not in attributi(r4), attributi(r4))

    print("\n5. Un «no» che arriva dentro lo slot note non diventa una nota")
    chiamate.clear()
    r5 = lambda_function.handler(
        envelope(intent_request("AddMovementIntent", {"amount": "9", "category": "bar"})), None
    )
    r5 = lambda_function.handler(
        envelope(
            intent_request("AddMovementIntent", {"amount": "9", "category": "bar", "note": "Niente"}),
            attributi(r5),
        ),
        None,
    )
    v.check("registra comunque", len(chiamate) == 1, chiamate)
    v.check("senza nota 'niente'", chiamate and "note" not in chiamate[0]["arguments"], chiamate)

    print("\n6. «Annulla» durante l'elicitazione scarta il movimento")
    chiamate.clear()
    r6 = lambda_function.handler(
        envelope(intent_request("AddMovementIntent", {"amount": "9", "category": "bar"})), None
    )
    r6 = lambda_function.handler(
        envelope(
            intent_request("AddMovementIntent", {"amount": "9", "category": "bar", "note": "annulla"}),
            attributi(r6),
        ),
        None,
    )
    v.check("nessuna registrazione", not chiamate, chiamate)
    v.check("lo dice all'utente", "non registro nulla" in parla(r6), parla(r6))
    v.check("attesa svuotata", "pending_movement" not in attributi(r6), attributi(r6))

    print("\n7. Sessione chiusa con un movimento in attesa: rete di sicurezza")
    chiamate.clear()
    r7 = lambda_function.handler(
        envelope(intent_request("AddMovementIntent", {"amount": "31", "category": "farmacia"})), None
    )
    lambda_function.handler(
        envelope(
            {
                "type": "SessionEndedRequest",
                "requestId": "amzn1.echo-api.request.end",
                "timestamp": "2026-10-20T10:01:00Z",
                "locale": "it-IT",
                "reason": "EXCEEDED_MAX_REPROMPTS",
            },
            attributi(r7),
        ),
        None,
    )
    v.check("il movimento viene registrato senza nota", len(chiamate) == 1, chiamate)
    v.check("importo giusto", chiamate and chiamate[0]["arguments"].get("amount") == "31", chiamate)

    print("\n8. Stop/Cancel e casi senza movimento in attesa")
    chiamate.clear()
    r8 = lambda_function.handler(
        envelope(intent_request("AddMovementIntent", {"amount": "5", "category": "bar"})), None
    )
    r8 = lambda_function.handler(envelope(intent_request("AMAZON.StopIntent"), attributi(r8)), None)
    v.check("Stop con movimento in attesa non registra", not chiamate, chiamate)
    v.check("Stop lo annulla esplicitamente", "non registro nulla" in parla(r8), parla(r8))

    r8b = lambda_function.handler(envelope(intent_request("AMAZON.StopIntent")), None)
    v.check("Stop senza nulla in attesa saluta", "A presto" in parla(r8b), parla(r8b))

    r8c = lambda_function.handler(envelope(intent_request("AMAZON.YesIntent")), None)
    v.check("«Sì» a freddo non va in errore", "errore" not in parla(r8c).lower(), parla(r8c))
    v.check("«Sì» a freddo spiega che non c'è nulla in sospeso",
            "nessun movimento in sospeso" in parla(r8c), parla(r8c))
    r8d = lambda_function.handler(envelope(intent_request("AMAZON.NoIntent")), None)
    v.check("«No» a freddo non va in errore", "errore" not in parla(r8d).lower(), parla(r8d))

    print("\n9. Account non collegato e sinonimi di KindType")
    chiamate.clear()
    r9 = lambda_function.handler(
        envelope(
            intent_request("AddMovementIntent", {"amount": "20", "category": "bar"}), access_token=None
        ),
        None,
    )
    card = (r9.get("response") or {}).get("card") or {}
    v.check("senza token risponde con LinkAccount", card.get("type") == "LinkAccount", card)
    v.check("niente chiamate al server", not chiamate, chiamate)

    # "incasso" è sinonimo di "entrata" in KindType: conta la resolution, non il parlato.
    richiesta = intent_request("AddMovementIntent", {"amount": "500", "category": "stipendio"})
    richiesta["intent"]["slots"]["kind"] = {
        "name": "kind",
        "value": "incasso",
        "confirmationStatus": "NONE",
        "resolutions": {
            "resolutionsPerAuthority": [
                {
                    "authority": "amzn1.er-authority.echo-sdk.test.KindType",
                    "status": {"code": "ER_SUCCESS_MATCH"},
                    "values": [{"value": {"name": "entrata", "id": "x"}}],
                }
            ]
        },
    }
    chiamate.clear()
    r9b = lambda_function.handler(envelope(richiesta), None)
    v.check("il sinonimo «incasso» viene riconosciuto come entrata",
            "entrata di 500 euro" in parla(r9b), parla(r9b))
    pend = attributi(r9b).get("pending_movement") or {}
    v.check("kind=income nel movimento in attesa", pend.get("kind") == "income", pend)

    print("\n" + "-" * 60)
    print("{} controlli superati, {} falliti".format(v.ok, v.ko))
    return 1 if v.ko else 0


if __name__ == "__main__":
    sys.exit(main())
