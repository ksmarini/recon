#!/usr/bin/env python3
import sys
import os
import subprocess
import uuid
from pathlib import Path
from time import strftime
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor, as_completed
from conn.database import get_opensearch_client

# Configurações
client = get_opensearch_client()
MAX_WORKERS = min(10, (os.cpu_count() or 1) * 2)  # Limita a 10 threads no máximo
TIMEOUT_NMAP = 1800  # 30 minutos em segundos
SCANNER = "nmap"


def get_unique_ips(index: str) -> list:
    """Busca IPs únicos válidos no OpenSearch, excluindo 0.0.0.0"""
    query = {
        "size": 0,
        "query": {"bool": {"must_not": {"term": {"server.ip.keyword": "0.0.0.0"}}}},
        "aggs": {
            "unique_ips": {"terms": {"field": "server.ip.keyword", "size": 10000}}
        },
    }

    try:
        response = client.search(index=index, body=query)
        return [
            bucket["key"]
            for bucket in response["aggregations"]["unique_ips"]["buckets"]
        ]
    except Exception as e:
        print(f"Erro ao buscar IPs: {e}")
        sys.exit(1)


def criar_diretorios(target: str) -> None:
    """Cria estrutura de diretórios para armazenar resultados"""
    Path(f"/docker/recon/data/{target}/temp").mkdir(parents=True, exist_ok=True)


def run_nmap(target: str, ip: str) -> str:
    """Executa o nmap em um container Docker"""
    scan_id = str(uuid.uuid1())[:8]
    output_file = f"/docker/recon/data/{target}/temp/nmap-{scan_id}.xml"

    cmd = (
        f"docker run --rm --name {target}-{scan_id}-nmap "
        f"-v /docker/recon/data/{target}/temp:/data "
        f"kali-tools:2.1 nmap -sSV -Pn {ip} "
        f"-oX /data/nmap-{scan_id}.xml --stylesheet=none"
    )

    try:
        subprocess.run(cmd, shell=True, check=True, timeout=TIMEOUT_NMAP)
        return output_file
    except subprocess.TimeoutExpired:
        print(f"[!] Timeout no scan de {ip}")
        return ""
    except Exception as e:
        print(f"[!] Falha no scan de {ip}: {str(e)[:100]}")
        return ""


def parse_nmap_results(xml_path: str, target: str) -> list:
    """Processa o XML do nmap e retorna documentos para o OpenSearch"""
    try:
        tree = ET.parse(xml_path)
        docs = []

        for host in tree.findall("host"):
            ip_element = host.find("address[@addrtype='ipv4']")
            if ip_element is None:
                continue

            ip = ip_element.get("addr", "")
            doc = {
                "@timestamp": strftime("%Y-%m-%dT%H:%M:%S%Z"),
                "server.ip": ip,
                "source_index": target,
                "scanner": SCANNER,
                "ports": [],
            }

            for port in host.findall("ports/port"):
                port_data = {
                    "port": port.get("portid", ""),
                    "protocol": port.get("protocol", ""),
                    "state": port.find("state").get("state", "")
                    if port.find("state") is not None
                    else "",
                }

                service = port.find("service")
                if service is not None:
                    port_data.update(
                        {
                            "service": service.get("name", ""),
                            "product": service.get("product", ""),
                            "version": service.get("version", ""),
                        }
                    )
                else:  # Garante campos mesmo sem serviço
                    port_data.update({"service": "", "product": "", "version": ""})

                doc["ports"].append(port_data)

            docs.append(doc)

        return docs
    except Exception as e:
        print(f"[!] Erro ao processar {xml_path}: {e}")
        return []


def main(target_index: str) -> None:
    """Execução principal com paralelismo"""
    output_index = f"{target_index}-portscan"
    ips = get_unique_ips(target_index)

    if not ips:
        print("[!] Nenhum IP válido encontrado para scan")
        return

    print(f"[*] Iniciando scan de {len(ips)} IPs com {MAX_WORKERS} threads...")

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = {}

        for ip in ips:
            future = executor.submit(lambda ip: (ip, run_nmap(target_index, ip)), ip)
            futures[future] = ip

        for future in as_completed(futures):
            ip = futures[future]
            try:
                _, xml_path = future.result()
                if not xml_path:
                    continue

                for doc in parse_nmap_results(xml_path, target_index):
                    client.index(index=output_index, body=doc)
                    print(f"\n[+] Dados indexados para {ip}")

            except Exception as e:
                print(f"[!] Erro crítico no IP {ip}: {e}")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(f"Uso: {sys.argv[0]} <indice_origem>")
        sys.exit(1)

    main(sys.argv[1])
