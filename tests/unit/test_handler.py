import base64
import json
import unittest

from hello_world import app


class GuiaHandlerTests(unittest.TestCase):
    def setUp(self):
        app.contador = 0

    def test_gera_guia_com_sucesso(self):
        event = {
            "httpMethod": "POST",
            "path": "/guias",
            "body": json.dumps(
                {
                    "requisicaoId": "R-001",
                    "hospital": "H-Recife",
                    "bolsas": ["O-NEG-0142"],
                }
            ),
        }

        ret = app.lambda_handler(event, None)
        data = json.loads(ret["body"])

        self.assertEqual(ret["statusCode"], 201)
        self.assertEqual(data["guia"], "G-R-001")
        self.assertEqual(data["hospital"], "H-Recife")
        self.assertEqual(data["bolsas"], ["O-NEG-0142"])
        self.assertEqual(data["invocacaoNesteAmbiente"], 1)

    def test_gera_guia_com_body_base64_do_sam_generate_event(self):
        payload = json.dumps(
            {
                "requisicaoId": "R-001",
                "hospital": "H-Recife",
                "bolsas": ["O-NEG-0142"],
            }
        )
        event = {
            "httpMethod": "POST",
            "path": "/guias",
            "isBase64Encoded": True,
            "body": base64.b64encode(payload.encode("utf-8")).decode("utf-8"),
        }

        ret = app.lambda_handler(event, None)
        data = json.loads(ret["body"])

        self.assertEqual(ret["statusCode"], 201)
        self.assertEqual(data["guia"], "G-R-001")
        self.assertEqual(data["hospital"], "H-Recife")
        self.assertEqual(data["bolsas"], ["O-NEG-0142"])

    def test_erro_quando_falta_requisicao_id(self):
        event = {
            "httpMethod": "POST",
            "path": "/guias",
            "body": json.dumps({"hospital": "H-Recife"}),
        }

        ret = app.lambda_handler(event, None)
        data = json.loads(ret["body"])

        self.assertEqual(ret["statusCode"], 400)
        self.assertEqual(data["erro"], "requisicaoId obrigatório")

    def test_contador_incrementa_no_mesmo_ambiente(self):
        event = {
            "httpMethod": "POST",
            "path": "/guias",
            "body": json.dumps({"requisicaoId": "R-002", "hospital": "H-Caruaru"}),
        }

        r1 = json.loads(app.lambda_handler(event, None)["body"])
        r2 = json.loads(app.lambda_handler(event, None)["body"])

        self.assertEqual(r1["invocacaoNesteAmbiente"], 1)
        self.assertEqual(r2["invocacaoNesteAmbiente"], 2)


if __name__ == "__main__":
    unittest.main()
