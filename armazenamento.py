"""Leitura/escrita dos ficheiros json e validações, sem depender do Qt
(assim dá para testar sem interface)."""
import json
import os
import re
import time
from contextlib import contextmanager
from urllib.parse import urlparse


class FicheiroCorrompido(Exception):
    """O ficheiro existe mas não tem json válido."""


def ler_json(caminho, se_falhar):
    # se o ficheiro não existe devolve o valor por defeito; se existe mas
    # está estragado levanta erro, para nunca ser sobrescrito sem querer
    try:
        with open(caminho, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return se_falhar
    except ValueError as erro:
        raise FicheiroCorrompido(f"{caminho}: {erro}") from erro


def gravar_json(caminho, dados):
    # grava num ficheiro temporário e só depois substitui, para um crash
    # a meio não deixar o json cortado
    os.makedirs(os.path.dirname(caminho), exist_ok=True)
    tmp = f"{caminho}.{os.getpid()}.tmp"
    try:
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(dados, f, indent=2, ensure_ascii=False)
        os.replace(tmp, caminho)
    finally:
        if os.path.exists(tmp):
            os.remove(tmp)


@contextmanager
def bloqueio(caminho, espera=5.0):
    """Exclusão mútua entre utilizadores numa pasta partilhada, através de
    um ficheiro .lock criado de forma atómica."""
    lock = caminho + ".lock"
    os.makedirs(os.path.dirname(lock), exist_ok=True)
    limite = time.monotonic() + espera
    while True:
        try:
            fd = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            os.close(fd)
            break
        except FileExistsError:
            try:
                # lock esquecido por um crash: passados 30s considera-se morto
                if time.time() - os.path.getmtime(lock) > 30:
                    os.remove(lock)
                    continue
            except OSError:
                pass
            if time.monotonic() > limite:
                raise TimeoutError("Ficheiro ocupado por outro utilizador, tente de novo.")
            time.sleep(0.1)
    try:
        yield
    finally:
        try:
            os.remove(lock)
        except OSError:
            pass


def alterar_lista(caminho, funcao):
    """Lê a lista, aplica `funcao(lista)` (que devolve a nova lista) e grava,
    tudo dentro do bloqueio, para dois utilizadores não se sobreporem."""
    with bloqueio(caminho):
        atual = ler_json(caminho, [])
        if not isinstance(atual, list):
            raise FicheiroCorrompido(f"{caminho}: esperava-se uma lista")
        gravar_json(caminho, funcao(atual))


def url_valido(url, hosts_permitidos=()):
    """Só aceita https (e, se indicado, só desses domínios). Evita que um
    json alterado abra file://, ms-msdt: ou páginas de phishing."""
    if not isinstance(url, str):
        return False
    p = urlparse(url.strip())
    if p.scheme != "https" or not p.hostname:
        return False
    if hosts_permitidos:
        return any(p.hostname == h or p.hostname.endswith("." + h)
                   for h in hosts_permitidos)
    return True


def filtrar_dashboards(lista, hosts_permitidos=()):
    if not isinstance(lista, list):
        return []
    return [d for d in lista
            if isinstance(d, dict) and d.get("nome") and url_valido(d.get("url"), hosts_permitidos)]


EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def email_valido(email):
    return bool(EMAIL_RE.match(email))
