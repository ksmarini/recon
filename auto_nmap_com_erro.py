#!/usr/bin/env python3

import sys
import subprocess
import uuid
import json
from pathlib import Path
from time import strftime
import xml.etree.ElementTree as ET
from conn.database import get_opensearch_client

host = "localhost"
port = 9200

client = get_opensearch_client()

target = sys.argv[1]
ip = sys.argv[2]
dic_nmap = {}
hora = strftime("%Y-%m-%dT%H:%M:%S%Z")
scanner = "nmap"
x = str(uuid.uuid1()).split("-")[0]
container_name = target + "-" + x + "-nmap"
saida = "nmap-" + x + ".xml"


def criar_diretorios(target: str) -> None:
    """Cria a estrutura de diretórios para o target dentro do ambiente Docker"""
    # Diretório principal do target
    dir_principal = Path(f"/docker/recon/data/{target}")
    # Diretório temporário para processamento
    dir_temp = dir_principal / "temp"

    # Cria ambos os diretórios (principal e temp)
    dir_temp.mkdir(parents=True, exist_ok=True)


def consulta(ip):
    """Consulta o OpenSearch para obter o bloco IP associado."""
    query = {"query": {"term": {"server.ip": ip}}}
    try:
        response = client.search(index="subdomains_index", body=query, size=1)
        if response["hits"]["hits"]:
            return response["hits"]["hits"][0]["_source"].get("server.ipblock", "")
    except Exception as e:
        print(f"Erro na consulta: {e}")
    return ""


def executa():
    criar_diretorios(target)

    comando = (
        f"docker run --rm --name {container_name} "
        f"-v /docker/recon/data/{target}/temp:/data "
        f"kali-tools:2.1 nmap -sSV -Pn {ip} -oX /data/{saida}"
    )

    # print(f"Executando comando:\n{comando}")
    subprocess.check_output(comando, shell=True)


def parse():
    index_name = f"nmap-{target}-{hora.replace(':', '-')}"
    tree = ET.parse("/docker/recon/data/" + target + "/temp/" + saida)
    root = tree.getroot()
    for i in root.iter("nmaprun"):
        for nmaprun in i:
            if nmaprun.tag == "host":
                for host in nmaprun:
                    if host.tag == "address":
                        if ":" not in host.attrib["addr"]:
                            dic_nmap["ipv4"] = host.attrib["addr"]
                            dic_nmap["addrtype"] = host.attrib["addrtype"]
                    if host.tag == "ports":
                        for port in host:
                            if port.tag == "port":
                                dic_nmap["network.transport"] = port.attrib["protocol"]
                                dic_nmap["server.port"] = port.attrib["portid"]
                                for itens in port:
                                    if itens.tag == "state":
                                        dic_nmap["service.state"] = itens.attrib[
                                            "state"
                                        ]
                                    if itens.tag == "service":
                                        try:
                                            dic_nmap["network.protocol"] = itens.attrib[
                                                "name"
                                            ]
                                        except:
                                            dic_nmap["network.protocol"] = ""
                                        try:
                                            dic_nmap["application.version.number"] = (
                                                itens.attrib["version"]
                                            )
                                        except:
                                            dic_nmap["application.version.number"] = ""
                                        try:
                                            dic_nmap["service.name"] = itens.attrib[
                                                "product"
                                            ]
                                        except:
                                            dic_nmap["service.name"] = ""
                                        dic_nmap["server.ipblock"] = consulta(ip)

                                        document = {
                                            "@timestamp": dic_nmap["timestamp"],
                                            "server.address": dic_nmap[
                                                "server.address"
                                            ],
                                            "server.domain": dic_nmap["server.domain"],
                                            "server.ip": dic_nmap["server.ip"],
                                            "server.ipblock": dic_nmap[
                                                "server.ipblock"
                                            ],
                                            "server.nameserver": dic_nmap[
                                                "server.nameserver"
                                            ],
                                            "vulnerability.scanner.vendor": dic_nmap[
                                                "vulnerability.scanner.vendor"
                                            ],
                                        }

                                        try:
                                            response = client.index(
                                                index=index_name,
                                                body=document,
                                            )
                                            print(
                                                f"Dados indexados em {index_name}: {response['_id']}"
                                            )
                                        except Exception as e:
                                            print(f"Erro ao indexar no OpenSearch: {e}")
                                        #
                                        # saida_completa = response.copy()
                                        # saida_completa["document"] = document
                                        #
                                        # print(saida_completa)  # Imprime os dados do cliente e os dados do banco
                                        # print(document) # Imprime os dados do cliente
                                        # print(response) # Imprime somente os dados do OpenSearch

                                        print(dic_nmap)


def main():
    executa()
    parse()


if __name__ == "__main__":
    main()
