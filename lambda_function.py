import logging


from ask_sdk_core.utils.predicate import is_intent_name, is_request_type


from ask_sdk_core.skill_builder import SkillBuilder
from ask_sdk_core.dispatch_components.request_components import AbstractRequestHandler
from ask_sdk_core.dispatch_components.exception_components import AbstractExceptionHandler
from ask_sdk_core.handler_input import HandlerInput

from ask_sdk_model.intent_request import IntentRequest
from ask_sdk_model.response import Response

from temagua import buscar_calendario_compesa

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

class VerificarAguaIntentHandler(AbstractRequestHandler):
    """Handler principal para buscar a água por bairro."""
    def can_handle(self, handler_input: HandlerInput) -> bool:
        return is_intent_name("VerificarAguaIntent")(handler_input)

    def handle(self, handler_input: HandlerInput) -> Response:
        attributes_manager = handler_input.attributes_manager 
        session_attributes = attributes_manager.session_attributes if attributes_manager.session_attributes is not None else {}
        request = handler_input.request_envelope.request
        
        if isinstance(request, IntentRequest):
            intent = request.intent
            slots = intent.slots if intent and intent.slots else {}
            
            bairro_slot = slots.get("bairro")
            bairro_solicitado = bairro_slot.value if bairro_slot and bairro_slot.value else None
            
            if not bairro_solicitado:
                return (
                    handler_input.response_builder
                        .speak("Desculpe, não consegui entender o nome do bairro. Pode repetir?")
                        .ask("Qual bairro você deseja consultar?")
                        .response
                )

            jaPerguntou = session_attributes.get("ultimo_Bairro_tentado") == bairro_solicitado
            resposta_texto = buscar_calendario_compesa(bairro_solicitado, jaPerguntou)
            
            if "MULTIPLO|" in resposta_texto:
                session_attributes["ultimo_Bairro_tentado"] = bairro_solicitado
                attributes_manager.session_attributes = session_attributes
                
                mensagem = resposta_texto.replace("MULTIPLO|", "")
                return (
                    handler_input.response_builder
                        .speak(mensagem)
                        .ask("Qual dessas opções você quis dizer?")
                        .response
                )

        else:
            resposta_texto = "Desculpe, houve um erro ao processar esse pedido."
        
        session_attributes["ultimo_Bairro_tentado"] = None
        attributes_manager.session_attributes = session_attributes

        return (
            handler_input.response_builder
                .speak(resposta_texto)
                .response
        )

class LaunchRequestHandler(AbstractRequestHandler):
    """Handler disparado ao abrir a skill sem comando específico."""
    def can_handle(self, handler_input: HandlerInput) -> bool:
        return is_request_type("LaunchRequest")(handler_input)

    def handle(self, handler_input: HandlerInput) -> Response:
        speak_output = "De qual bairro você quer saber a previsão de abastecimento?"
        return (
            handler_input.response_builder
                .speak(speak_output)
                .ask(speak_output)
                .response
        )

class HelpIntentHandler(AbstractRequestHandler):
    def can_handle(self, handler_input):
        return is_intent_name("AMAZON.HelpIntent")(handler_input)

    def handle(self, handler_input):
        speak = "Você pode perguntar, por exemplo: tem água em Boa Viagem."
        return handler_input.response_builder.speak(speak).ask(speak).response


class CancelAndStopIntentHandler(AbstractRequestHandler):
    def can_handle(self, handler_input):
        return (
            is_intent_name("AMAZON.CancelIntent")(handler_input) or
            is_intent_name("AMAZON.StopIntent")(handler_input)
        )

    def handle(self, handler_input):
        return handler_input.response_builder.speak("Até mais!").response


class FallbackIntentHandler(AbstractRequestHandler):
    def can_handle(self, handler_input):
        return is_intent_name("AMAZON.FallbackIntent")(handler_input)

    def handle(self, handler_input):
        speak = "Não entendi. Diga, por exemplo: tem água em Boa Viagem?"
        return handler_input.response_builder.speak(speak).ask(speak).response


class SessionEndedRequestHandler(AbstractRequestHandler):
    """Handler para encerramento de sessão."""
    def can_handle(self, handler_input: HandlerInput) -> bool:
        return is_request_type("SessionEndedRequest")(handler_input)

    def handle(self, handler_input: HandlerInput) -> Response:
        return handler_input.response_builder.response

class CatchAllExceptionHandler(AbstractExceptionHandler):
    """Tratamento de erros globais para evitar que a skill pare de responder."""
    def can_handle(self, handler_input: HandlerInput, exception: Exception) -> bool:
        return True

    def handle(self, handler_input: HandlerInput, exception: Exception) -> Response:
        logger.error(f"Erro capturado: {exception}", exc_info=True)
        return (
            handler_input.response_builder
                .speak("Desculpe, não consegui acessar o sistema agora. Tente novamente em instantes.")
                .response
        )

sb = SkillBuilder()

sb.add_request_handler(LaunchRequestHandler())
sb.add_request_handler(VerificarAguaIntentHandler())
sb.add_request_handler(HelpIntentHandler())
sb.add_request_handler(FallbackIntentHandler())
sb.add_request_handler(CancelAndStopIntentHandler())
sb.add_request_handler(SessionEndedRequestHandler())
sb.add_exception_handler(CatchAllExceptionHandler())

lambda_handler = sb.lambda_handler()