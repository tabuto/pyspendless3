import logging
import os

import requests
from ask_sdk_core.dispatch_components import AbstractRequestHandler, AbstractExceptionHandler
from ask_sdk_core.skill_builder import SkillBuilder
from ask_sdk_core.utils import is_request_type, is_intent_name
from ask_sdk_core.handler_input import HandlerInput
from ask_sdk_model import Response
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
    slots = handler_input.request_envelope.request.intent.slots
    slot = slots.get(slot_name) if slots else None
    return slot.value if slot and slot.value else None


class LaunchRequestHandler(AbstractRequestHandler):
    def can_handle(self, handler_input: HandlerInput) -> bool:
        return is_request_type("LaunchRequest")(handler_input)

    def handle(self, handler_input: HandlerInput) -> Response:
        speech = "Ciao, sono PySpendless. Puoi dirmi ad esempio: registra una spesa di 20 euro per spesa alimentare."
        return handler_input.response_builder.speak(speech).ask(speech).response


class AddMovementIntentHandler(AbstractRequestHandler):
    def can_handle(self, handler_input: HandlerInput) -> bool:
        return is_intent_name("AddMovementIntent")(handler_input)

    def handle(self, handler_input: HandlerInput) -> Response:
        access_token = get_access_token(handler_input)
        if not access_token:
            return _link_account_response(handler_input)

        amount = _slot_value(handler_input, "amount")
        category = _slot_value(handler_input, "category")

        if amount is None or category is None:
            speech = "Mi serve sia l'importo che la categoria, ad esempio: registra 15 euro per trasporti."
            return handler_input.response_builder.speak(speech).ask(speech).response

        arguments = {"amount": amount, "category": category}

        kind = _slot_value(handler_input, "kind")
        if kind == "entrata":
            arguments["kind"] = "income"

        wallet = _slot_value(handler_input, "wallet")
        if wallet:
            arguments["wallet"] = wallet

        note = _slot_value(handler_input, "note")
        if note:
            arguments["note"] = note

        try:
            text, _ = call_mcp_tool(access_token, "add_movement", arguments)
        except McpAuthError:
            return _link_account_response(handler_input)
        except requests.RequestException:
            logger.exception("Chiamata a add_movement fallita")
            text = GENERIC_ERROR_SPEECH

        return handler_input.response_builder.speak(text).ask("Altro?").response


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
            text, _ = call_mcp_tool(access_token, "list_categories", arguments)
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
            "'registra 20 euro per spesa alimentare', oppure chiedermi quali categorie hai disponibili."
        )
        return handler_input.response_builder.speak(speech).ask(speech).response


class CancelOrStopIntentHandler(AbstractRequestHandler):
    def can_handle(self, handler_input: HandlerInput) -> bool:
        return is_intent_name("AMAZON.CancelIntent")(handler_input) or is_intent_name("AMAZON.StopIntent")(
            handler_input
        )

    def handle(self, handler_input: HandlerInput) -> Response:
        return handler_input.response_builder.speak("A presto.").response


class FallbackIntentHandler(AbstractRequestHandler):
    def can_handle(self, handler_input: HandlerInput) -> bool:
        return is_intent_name("AMAZON.FallbackIntent")(handler_input)

    def handle(self, handler_input: HandlerInput) -> Response:
        speech = "Non ho capito. Puoi chiedermi di registrare un movimento o elencare le categorie."
        return handler_input.response_builder.speak(speech).ask(speech).response


class SessionEndedRequestHandler(AbstractRequestHandler):
    def can_handle(self, handler_input: HandlerInput) -> bool:
        return is_request_type("SessionEndedRequest")(handler_input)

    def handle(self, handler_input: HandlerInput) -> Response:
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
sb.add_request_handler(AddMovementIntentHandler())
sb.add_request_handler(ListCategoriesIntentHandler())
sb.add_request_handler(HelpIntentHandler())
sb.add_request_handler(CancelOrStopIntentHandler())
sb.add_request_handler(FallbackIntentHandler())
sb.add_request_handler(SessionEndedRequestHandler())
sb.add_exception_handler(CatchAllExceptionHandler())

handler = sb.lambda_handler()
