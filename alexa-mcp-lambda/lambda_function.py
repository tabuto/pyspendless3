import logging
import os

import requests
from ask_sdk_core.dispatch_components import AbstractRequestHandler, AbstractExceptionHandler
from ask_sdk_core.skill_builder import SkillBuilder
from ask_sdk_core.utils import is_request_type, is_intent_name
from ask_sdk_core.handler_input import HandlerInput
from ask_sdk_model import Response, Intent, Slot
from ask_sdk_model.dialog import ElicitSlotDirective
from ask_sdk_model.ui import LinkAccountCard

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

MCP_SERVER_URL = os.environ.get("MCP_SERVER_URL", "https://tabuto.pythonanywhere.com/mcp-oauth2")
MCP_TIMEOUT_SECONDS = 8

LINK_ACCOUNT_SPEECH = (
    "Devi prima collegare il tuo account PySpendless. "
    "Apri l'app Alexa sul telefono e segui le istruzioni per il collegamento."
)
GENERIC_ERROR_SPEECH = "Non sono riuscita a contattare PySpendless, riprova tra poco."

# Movimento in attesa di risposta alla domanda sulla nota. Vive negli attributi
# di sessione, che Alexa rimanda indietro a ogni turno: la Lambda resta senza
# stato proprio, nessun database di appoggio.
PENDING_KEY = "pending_movement"

ASK_NOTE_SPEECH = "Vuoi aggiungere una nota?"
ELICIT_NOTE_SPEECH = "Dimmi la nota."

# Risposte che durante l'elicitazione della nota NON sono una nota. Mentre Alexa
# elicita uno slot AMAZON.SearchQuery, qualunque frase finisce nello slot: un
# "no" detto in quel turno arriverebbe come nota con testo "no".
NOTE_DECLINED = {
    "no", "no grazie", "niente", "nessuna", "nessuna nota", "non importa",
    "lascia stare", "va bene così", "basta",
}
NOTE_CANCELLED = {"annulla", "cancella", "lascia perdere", "annullare"}


class McpAuthError(Exception):
    """Token di accesso mancante, scaduto o rifiutato dal server MCP (401/403)."""


def get_access_token(handler_input: HandlerInput):
    return handler_input.request_envelope.context.system.user.access_token


def call_mcp_tool(access_token: str, tool_name: str, arguments: dict):
    response = requests.post(
        MCP_SERVER_URL,
        headers={"Authorization": "Bearer {}".format(access_token)},
        json={
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {"name": tool_name, "arguments": arguments},
        },
        timeout=MCP_TIMEOUT_SECONDS,
    )

    if response.status_code in (401, 403):
        raise McpAuthError()
    response.raise_for_status()

    body = response.json()
    if "error" in body:
        return body["error"].get("message", "Errore del server."), True

    result = body.get("result", {})
    content = result.get("content") or []
    text = content[0]["text"] if content and "text" in content[0] else "Nessuna risposta dal server."
    return text, result.get("isError", False)


def _link_account_response(handler_input: HandlerInput) -> Response:
    return (
        handler_input.response_builder.speak(LINK_ACCOUNT_SPEECH)
        .set_card(LinkAccountCard())
        .response
    )


def _slot_value(handler_input: HandlerInput, slot_name: str):
    """
    Valore di uno slot, preferendo il valore CANONICO risolto dallo slot type
    custom: se l'utente dice "uscita" (sinonimo) lo slot `value` è "uscita",
    mentre le resolutions riportano "spesa", che è quello che sa interpretare il
    server. Senza match si ripiega sul parlato grezzo (gli slot type custom non
    sono una whitelist chiusa, e il server fa comunque un confronto normalizzato).
    """
    slots = handler_input.request_envelope.request.intent.slots
    slot = slots.get(slot_name) if slots else None
    if not slot:
        return None

    resolutions = getattr(slot, "resolutions", None)
    per_authority = getattr(resolutions, "resolutions_per_authority", None) if resolutions else None
    for authority in per_authority or []:
        status = getattr(getattr(authority, "status", None), "code", None)
        values = getattr(authority, "values", None) or []
        if str(status).endswith("ER_SUCCESS_MATCH") and values:
            return values[0].value.name

    return slot.value if slot.value else None


def _session(handler_input: HandlerInput) -> dict:
    return handler_input.attributes_manager.session_attributes


def _pending(handler_input: HandlerInput):
    return _session(handler_input).get(PENDING_KEY)


def _clear_pending(handler_input: HandlerInput):
    _session(handler_input).pop(PENDING_KEY, None)


def _movement_summary(arguments: dict) -> str:
    kind = "entrata" if arguments.get("kind") == "income" else "spesa"
    return "Ho una {} di {} euro per {}.".format(kind, arguments.get("amount"), arguments.get("category"))


def _slots_from_arguments(arguments: dict) -> dict:
    """
    Ricostruisce gli slot di AddMovementIntent per `updatedIntent` di
    ElicitSlotDirective: Alexa, al turno dopo, rimanda l'intent con questi
    valori già riempiti, così non richiede importo e categoria.
    """
    values = {
        "amount": arguments.get("amount"),
        "category": arguments.get("category"),
        "wallet": arguments.get("wallet"),
        "kind": "entrata" if arguments.get("kind") == "income" else None,
    }
    return {name: Slot(name=name, value=value) for name, value in values.items() if value}


def _register(handler_input: HandlerInput, arguments: dict, note: str = None) -> Response:
    """Chiama add_movement e consuma il movimento in attesa."""
    access_token = get_access_token(handler_input)
    if not access_token:
        return _link_account_response(handler_input)

    payload = dict(arguments)
    if note:
        payload["note"] = note

    _clear_pending(handler_input)

    try:
        text, is_error = call_mcp_tool(access_token, "add_movement", payload)
        logger.info("add_movement args=%s isError=%s esito=%s", payload, is_error, text[:120])
    except McpAuthError:
        logger.info("add_movement: token rifiutato dal server, chiedo di ricollegare l'account")
        return _link_account_response(handler_input)
    except requests.RequestException:
        logger.exception("Chiamata a add_movement fallita")
        text = GENERIC_ERROR_SPEECH

    return handler_input.response_builder.speak(text).ask("Altro?").response


class LaunchRequestHandler(AbstractRequestHandler):
    def can_handle(self, handler_input: HandlerInput) -> bool:
        return is_request_type("LaunchRequest")(handler_input)

    def handle(self, handler_input: HandlerInput) -> Response:
        speech = "Ciao, sono PySpendless. Puoi dirmi ad esempio: registra una spesa di 20 euro per spesa alimentare."
        return handler_input.response_builder.speak(speech).ask(speech).response


class AddMovementIntentHandler(AbstractRequestHandler):
    """
    Primo turno: raccoglie importo e categoria e chiede se aggiungere una nota,
    SENZA registrare nulla. Turno dell'elicitazione: arriva lo stesso intent con
    lo slot `note` riempito, e lì il movimento viene registrato.
    """

    def can_handle(self, handler_input: HandlerInput) -> bool:
        return is_intent_name("AddMovementIntent")(handler_input)

    def handle(self, handler_input: HandlerInput) -> Response:
        access_token = get_access_token(handler_input)
        if not access_token:
            return _link_account_response(handler_input)

        note = _slot_value(handler_input, "note")
        pending = _pending(handler_input)

        # Turno di risposta alla domanda sulla nota.
        if note is not None and pending:
            spoken = note.strip().lower()
            if spoken in NOTE_CANCELLED:
                _clear_pending(handler_input)
                logger.info("movimento in attesa annullato durante l'elicitazione della nota")
                return handler_input.response_builder.speak("Ok, non registro nulla.").response
            if spoken in NOTE_DECLINED:
                logger.info("nota rifiutata a voce durante l'elicitazione, registro senza nota")
                return _register(handler_input, pending)
            return _register(handler_input, pending, note=note)

        amount = _slot_value(handler_input, "amount")
        category = _slot_value(handler_input, "category")

        if amount is None or category is None:
            speech = "Mi serve sia l'importo che la categoria, ad esempio: registra 15 euro per trasporti."
            return handler_input.response_builder.speak(speech).ask(speech).response

        arguments = {"amount": amount, "category": category}

        if _slot_value(handler_input, "kind") == "entrata":
            arguments["kind"] = "income"

        wallet = _slot_value(handler_input, "wallet")
        if wallet:
            arguments["wallet"] = wallet

        _session(handler_input)[PENDING_KEY] = arguments
        logger.info("movimento in attesa della nota: %s", arguments)

        speech = "{} {}".format(_movement_summary(arguments), ASK_NOTE_SPEECH)
        return handler_input.response_builder.speak(speech).ask(ASK_NOTE_SPEECH).response


class YesIntentHandler(AbstractRequestHandler):
    """«Sì» alla domanda sulla nota: elicita lo slot `note` di AddMovementIntent."""

    def can_handle(self, handler_input: HandlerInput) -> bool:
        return is_intent_name("AMAZON.YesIntent")(handler_input) and bool(_pending(handler_input))

    def handle(self, handler_input: HandlerInput) -> Response:
        pending = _pending(handler_input)
        return (
            handler_input.response_builder.speak(ELICIT_NOTE_SPEECH)
            .ask(ELICIT_NOTE_SPEECH)
            .add_directive(
                ElicitSlotDirective(
                    slot_to_elicit="note",
                    updated_intent=Intent(
                        name="AddMovementIntent", slots=_slots_from_arguments(pending)
                    ),
                )
            )
            .response
        )


class NoIntentHandler(AbstractRequestHandler):
    """«No» alla domanda sulla nota: registra il movimento senza nota."""

    def can_handle(self, handler_input: HandlerInput) -> bool:
        return is_intent_name("AMAZON.NoIntent")(handler_input) and bool(_pending(handler_input))

    def handle(self, handler_input: HandlerInput) -> Response:
        return _register(handler_input, _pending(handler_input))


class YesNoWithoutPendingHandler(AbstractRequestHandler):
    """
    «Sì»/«no» detti fuori contesto. Senza questo handler nessuno raccoglie i due
    intent (quelli sopra pretendono un movimento in attesa), il dispatcher
    solleva un'eccezione e l'utente si sente dire «si è verificato un errore».
    """

    def can_handle(self, handler_input: HandlerInput) -> bool:
        return is_intent_name("AMAZON.YesIntent")(handler_input) or is_intent_name("AMAZON.NoIntent")(
            handler_input
        )

    def handle(self, handler_input: HandlerInput) -> Response:
        speech = (
            "Non ho nessun movimento in sospeso. Puoi dirmi ad esempio: "
            "registra 20 euro per spesa alimentare."
        )
        return handler_input.response_builder.speak(speech).ask(speech).response


class ListCategoriesIntentHandler(AbstractRequestHandler):
    def can_handle(self, handler_input: HandlerInput) -> bool:
        return is_intent_name("ListCategoriesIntent")(handler_input)

    def handle(self, handler_input: HandlerInput) -> Response:
        access_token = get_access_token(handler_input)
        if not access_token:
            return _link_account_response(handler_input)

        arguments = {}
        kind = _slot_value(handler_input, "kind")
        if kind == "entrata":
            arguments["kind"] = "income"
        elif kind == "spesa":
            arguments["kind"] = "expense"

        try:
            text, is_error = call_mcp_tool(access_token, "list_categories", arguments)
            logger.info("list_categories args=%s isError=%s", arguments, is_error)
        except McpAuthError:
            return _link_account_response(handler_input)
        except requests.RequestException:
            logger.exception("Chiamata a list_categories fallita")
            text = GENERIC_ERROR_SPEECH

        return handler_input.response_builder.speak(text).ask("Altro?").response


class HelpIntentHandler(AbstractRequestHandler):
    def can_handle(self, handler_input: HandlerInput) -> bool:
        return is_intent_name("AMAZON.HelpIntent")(handler_input)

    def handle(self, handler_input: HandlerInput) -> Response:
        speech = (
            "Puoi chiedermi di registrare una spesa o un'entrata, ad esempio "
            "'registra 20 euro per spesa alimentare': ti chiederò se vuoi aggiungere una nota. "
            "Oppure chiedimi quali categorie hai disponibili."
        )
        return handler_input.response_builder.speak(speech).ask(speech).response


class CancelOrStopIntentHandler(AbstractRequestHandler):
    def can_handle(self, handler_input: HandlerInput) -> bool:
        return is_intent_name("AMAZON.CancelIntent")(handler_input) or is_intent_name("AMAZON.StopIntent")(
            handler_input
        )

    def handle(self, handler_input: HandlerInput) -> Response:
        if _pending(handler_input):
            _clear_pending(handler_input)
            logger.info("movimento in attesa annullato da Cancel/Stop")
            return handler_input.response_builder.speak("Ok, non registro nulla.").response
        return handler_input.response_builder.speak("A presto.").response


class FallbackIntentHandler(AbstractRequestHandler):
    def can_handle(self, handler_input: HandlerInput) -> bool:
        return is_intent_name("AMAZON.FallbackIntent")(handler_input)

    def handle(self, handler_input: HandlerInput) -> Response:
        if _pending(handler_input):
            speech = "Non ho capito. {}".format(ASK_NOTE_SPEECH)
            return handler_input.response_builder.speak(speech).ask(ASK_NOTE_SPEECH).response
        speech = "Non ho capito. Puoi chiedermi di registrare un movimento o elencare le categorie."
        return handler_input.response_builder.speak(speech).ask(speech).response


class SessionEndedRequestHandler(AbstractRequestHandler):
    """
    Rete di sicurezza: se la sessione finisce con un movimento ancora in attesa
    della nota (l'utente si allontana, o scade il reprompt), il movimento viene
    registrato comunque senza nota. L'intenzione dichiarata era registrarlo, e
    perderlo in silenzio sarebbe peggio; un doppione è escluso dal controllo
    anti-duplicato del server. La risposta non viene resa da Alexa.
    """

    def can_handle(self, handler_input: HandlerInput) -> bool:
        return is_request_type("SessionEndedRequest")(handler_input)

    def handle(self, handler_input: HandlerInput) -> Response:
        pending = _pending(handler_input)
        if pending:
            logger.info("sessione chiusa con un movimento in attesa: lo registro senza nota")
            _register(handler_input, pending)
        return handler_input.response_builder.response


class CatchAllExceptionHandler(AbstractExceptionHandler):
    def can_handle(self, handler_input: HandlerInput, exception: Exception) -> bool:
        return True

    def handle(self, handler_input: HandlerInput, exception: Exception) -> Response:
        logger.exception("Errore non gestito")
        speech = "Si è verificato un errore, riprova."
        return handler_input.response_builder.speak(speech).ask(speech).response


sb = SkillBuilder()
sb.add_request_handler(LaunchRequestHandler())
sb.add_request_handler(YesIntentHandler())
sb.add_request_handler(NoIntentHandler())
sb.add_request_handler(YesNoWithoutPendingHandler())
sb.add_request_handler(AddMovementIntentHandler())
sb.add_request_handler(ListCategoriesIntentHandler())
sb.add_request_handler(HelpIntentHandler())
sb.add_request_handler(CancelOrStopIntentHandler())
sb.add_request_handler(FallbackIntentHandler())
sb.add_request_handler(SessionEndedRequestHandler())
sb.add_exception_handler(CatchAllExceptionHandler())

handler = sb.lambda_handler()
