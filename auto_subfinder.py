#!/usr/bin/env python3

import sys
import socket
import requests
import subprocess
import uuid
import json
from pathlib import Path
from time import strftime
from conn.database import get_opensearch_client

host = "localhost"
port = 9200

client = get_opensearch_client()

target = sys.argv[1]
domain = sys.argv[2]
dic_subfinder = {}
hora = strftime("%Y-%m-%dT%H:%M:%S%Z")
scanner = "subfinder"
x = str(uuid.uuid1()).split("-")[0]
container_name = target + "-" + x + "-subfinder"
saida = "subfinder-" + x + ".txt"


def criar_diretorios(target: str) -> None:
    """Cria a estrutura de diretórios para o target dentro do ambiente Docker"""
    # Diretório principal do target
    dir_principal = Path(f"/docker/recon/data/{target}")
    # Diretório temporário para processamento
    dir_temp = dir_principal / "temp"

    # Cria ambos os diretórios (principal e temp)
    dir_temp.mkdir(parents=True, exist_ok=True)


def rdap_ip(ip):
    try:
        consulta1 = subprocess.check_output(
            "docker run --rm --name "
            + container_name
            + " -v /docker/recon/data/"
            + target
            + ":/data kali-tools:2.1 rdap "
            + ip
            + " --json || true",
            shell=True,
        )
        json_rdap_ip = json.loads(consulta1)
        blocoip = json_rdap_ip["handle"]
        return blocoip
    except:
        return ""


def rdap_domain(domain):
    nameserver = ""
    try:
        consulta2 = requests.get("https://rdap.registro.br/domain/" + domain)
        json_rdap = json.loads(consulta2.text)
        for ns in json_rdap["nameservers"]:
            nameserver = nameserver + ns["ldhName"] + ","
        return nameserver[:-1]
    except:
        return ""


def executa():
    criar_diretorios(target)

    comando = (
        "docker run --rm --name "
        + container_name
        + " -v /docker/recon/data/"
        + target
        + "/temp:/data"
        + " kali-tools:2.1 subfinder -d "
        + domain
        + " -oJ -silent"
        + " >> /docker/recon/data/"
        + target
        + "/temp/"
        + saida
        + " || true"
    )

    # print(f"Executando comando:\n{comando}")
    subprocess.check_output(comando, shell=True)


def parse():
    index_name = target
    with open("/docker/recon/data/" + target + "/temp/" + saida) as json_file:
        for line in json_file:
            json_line = line.rstrip("\n")
            jsondata = json.loads(json_line)
            dic_subfinder["timestamp"] = hora
            dic_subfinder["server.address"] = jsondata["host"]
            dic_subfinder["server.domain"] = jsondata["host"]
            try:
                dic_subfinder["server.ip"] = socket.gethostbyname(jsondata["host"])
            except:
                dic_subfinder["server.ip"] = "0.0.0.0"
            dic_subfinder["vulnerability.scanner.vendor"] = scanner
            dic_subfinder["server.ipblock"] = rdap_ip(dic_subfinder["server.ip"])
            dic_subfinder["server.nameserver"] = rdap_domain(
                dic_subfinder["server.domain"]
            )

            document = {
                "@timestamp": dic_subfinder["timestamp"],
                "server.address": dic_subfinder["server.address"],
                "server.domain": dic_subfinder["server.domain"],
                "server.ip": dic_subfinder["server.ip"],
                "server.ipblock": dic_subfinder["server.ipblock"],
                "server.nameserver": dic_subfinder["server.nameserver"],
                "vulnerability.scanner.vendor": dic_subfinder[
                    "vulnerability.scanner.vendor"
                ],
            }

            response = client.index(
                index=index_name,
                body=document,
            )
            saida_completa = response.copy()
            saida_completa["document"] = document

            print(saida_completa)  # Imprime os dados do cliente e os dados do banco
            # print(document) # Imprime os dados do cliente
            # print(response) # Imprime somente os dados do OpenSearch


def main():
    executa()
    parse()


if __name__ == "__main__":
    main()
