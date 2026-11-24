import base64
import json
import time

contador = 0  # variável global: só sobrevive se o ambiente for reaproveitado


def lambda_handler(event, context):
    global contador
    contador += 1
    raw_body = event.get("body") or "{}"
    if event.get("isBase64Encoded"):
        raw_body = base64.b64decode(raw_body).decode("utf-8")
    pedido = json.loads(raw_body)
    if "requisicaoId" not in pedido:
        return {
            "statusCode": 400,
            "body": json.dumps({"erro": "requisicaoId obrigatório"}),
        }
    if pedido.get("demorar"):
        time.sleep(5)  # passa do Timeout de 3 s do template
    guia = {
        "guia": "G-" + pedido["requisicaoId"],
        "hospital": pedido.get("hospital"),
        "bolsas": pedido.get("bolsas", []),
        "invocacaoNesteAmbiente": contador,
    }
    return {"statusCode": 201, "body": json.dumps(guia)}
