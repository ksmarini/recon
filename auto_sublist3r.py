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
dic_sublist3r = {}
hora = strftime("%Y-%m-%dT%H:%M:%S%Z")
scanner = "sublist3r"
x = str(uuid.uuid1()).split("-")[0]
container_name = target + "-" + x + "-sublist3r"
saida = "sublist3r-" + x + ".txt"


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
            + ":/data kali-tools:2.0 rdap "
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
        + " kali-tools:2.1 /scripts/Sublist3r/sublist3r.py"
        + " -d "
        + domain
        + " -o /data/"
        + saida
        + " || true"
    )

    print(f"Executando comando:\n{comando}")
    subprocess.check_output(comando, shell=True)


def parse():
    index_name = target
    with open("/docker/recon/data/" + target + "/temp/" + saida) as file:
        for line in file:
            dic_sublist3r["timestamp"] = hora
            dic_sublist3r["server.address"] = line.rstrip("\n")
            dic_sublist3r["server.domain"] = line.rstrip("\n")
            try:
                dic_sublist3r["server.ip"] = socket.gethostbyname(line.rstrip("\n"))
            except:
                dic_sublist3r["server.ip"] = "0.0.0.0"
            dic_sublist3r["vulnerability.scanner.vendor"] = scanner
            dic_sublist3r["server.ipblock"] = rdap_ip(dic_sublist3r["server.ip"])
            dic_sublist3r["server.nameserver"] = rdap_domain(
                dic_sublist3r["server.domain"]
            )

            document = {
                "@timestamp": dic_sublist3r["timestamp"],
                "server.address": dic_sublist3r["server.address"],
                "server.domain": dic_sublist3r["server.domain"],
                "server.ip": dic_sublist3r["server.ip"],
                "server.ipblock": dic_sublist3r["server.ipblock"],
                "server.nameserver": dic_sublist3r["server.nameserver"],
                "vulnerability.scanner.vendor": dic_sublist3r[
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
