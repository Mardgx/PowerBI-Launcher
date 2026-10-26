import json
import os
import tempfile
import threading
import unittest

from armazenamento import (
    FicheiroCorrompido, ler_json, gravar_json, alterar_lista,
    url_valido, filtrar_dashboards, email_valido
)


class TestJson(unittest.TestCase):
    def setUp(self):
        self.pasta = tempfile.TemporaryDirectory()
        self.f = os.path.join(self.pasta.name, "dados", "x.json")

    def tearDown(self):
        self.pasta.cleanup()

    def test_ficheiro_em_falta_devolve_defeito(self):
        self.assertEqual(ler_json(self.f, []), [])

    def test_ficheiro_corrompido_levanta_erro_e_nao_e_sobrescrito(self):
        os.makedirs(os.path.dirname(self.f))
        with open(self.f, "w") as fh:
            fh.write("[{")
        with self.assertRaises(FicheiroCorrompido):
            alterar_lista(self.f, lambda l: l + [1])
        with open(self.f) as fh:
            self.assertEqual(fh.read(), "[{")

    def test_objeto_em_vez_de_lista_e_recusado(self):
        gravar_json(self.f, {"a": 1})
        with self.assertRaises(FicheiroCorrompido):
            alterar_lista(self.f, lambda l: l)

    def test_escritas_concorrentes_nao_perdem_dados(self):
        def escrever(i):
            alterar_lista(self.f, lambda l: l + [i])
        ts = [threading.Thread(target=escrever, args=(i,)) for i in range(15)]
        for t in ts:
            t.start()
        for t in ts:
            t.join()
        self.assertEqual(sorted(ler_json(self.f, [])), list(range(15)))
        self.assertEqual(os.listdir(os.path.dirname(self.f)), ["x.json"])


class TestValidacao(unittest.TestCase):
    def test_urls(self):
        self.assertTrue(url_valido("https://app.powerbi.com/groups/x"))
        for mau in ("http://app.powerbi.com", "file:///C:/x", "ms-msdt:/id",
                    "javascript:alert(1)", "https://", "", None, 5):
            self.assertFalse(url_valido(mau), mau)

    def test_hosts_permitidos(self):
        h = ("app.powerbi.com",)
        self.assertTrue(url_valido("https://app.powerbi.com/x", h))
        self.assertFalse(url_valido("https://app.powerbi.com.evil.io/x", h))
        self.assertFalse(url_valido("https://evilapp.powerbi.com.br/x", h))

    def test_filtrar_dashboards(self):
        ok = {"nome": "A", "url": "https://app.powerbi.com"}
        lista = [ok, {"nome": "B", "url": "file:///x"}, {"url": "https://a.b"}, 3, None]
        self.assertEqual(filtrar_dashboards(lista), [ok])
        self.assertEqual(filtrar_dashboards({"nome": "A"}), [])

    def test_email(self):
        self.assertTrue(email_valido("a@b.pt"))
        for mau in ("@", "a@", "a@b", "a b@c.pt", ""):
            self.assertFalse(email_valido(mau), mau)


if __name__ == "__main__":
    unittest.main()
