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
MAX_WORKERS = min(10, (os.cpu_count() or 1) * 2)  # Limita a 10 threads
TIMEOUT_NMAP = 1800  # 30 minutos em segundos
SCANNER = "nmap"


def get_unique_ips(index: str) -> list:
    """Versão corrigida da função de busca de IPs"""
    try:
        if not client.indices.exists(index=index):
            print(f"[!] Índice {index} não encontrado")
            return []

        # Tenta campos alternativos em ordem
        for field in [
            "server.ip.keyword",
            "network.ipv4.keyword",
            "network.ipv6.keyword",
        ]:
            query = {
                "size": 0,
                "query": {
                    "bool": {
                        "must": [{"exists": {"field": field}}],
                        "must_not": [
                            {"term": {field: "0.0.0.0"}},
                            {"term": {field: "::"}},
                        ],
                    }
                },
                "aggs": {"unique_ips": {"terms": {"field": field, "size": 10000}}},
            }

            response = client.search(index=index, body=query)
            buckets = response["aggregations"]["unique_ips"]["buckets"]
            if buckets:
                return [bucket["key"] for bucket in buckets]

        return []

    except Exception as e:
        print(f"[!] Erro na consulta: {str(e)}")
        return []


def criar_diretorios(target: str) -> None:
    """Cria estrutura de diretórios para resultados"""
    Path(f"/docker/recon/data/{target}/temp").mkdir(parents=True, exist_ok=True)


def run_nmap(target: str, ip: str) -> str:
    """Executa scan nmap (IPv4/IPv6) via Docker"""
    scan_id = str(uuid.uuid1())[:8]
    output_file = f"/docker/recon/data/{target}/temp/nmap-{scan_id}.xml"

    # Detecta automaticamente o tipo de IP
    ip_param = f"-6 {ip}" if ":" in ip else ip

    cmd = (
        f"docker run --rm --name {target}-{scan_id}-nmap "
        f"-v /docker/recon/data/{target}/temp:/data "
        f"kali-tools:2.1 nmap -sSV -Pn {ip_param} "
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
    """Processa XML incluindo IPv4/IPv6 e campos vazios como string"""
    try:
        tree = ET.parse(xml_path)
        docs = []

        for host in tree.findall("host"):
            # Coleta todos os endereços
            addresses = {
                addr.get("addrtype"): addr.get("addr", "")
                for addr in host.findall("address")
                if addr.get("addrtype") in ["ipv4", "ipv6", "mac"]
            }

            if not addresses:
                continue

            doc = {
                "@timestamp": strftime("%Y-%m-%dT%H:%M:%S%Z"),
                "source_index": target,
                "scanner": SCANNER,
                "network": addresses,
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
                port_data.update(
                    {
                        "service": service.get("name", "")
                        if service is not None
                        else "",
                        "product": service.get("product", "")
                        if service is not None
                        else "",
                        "version": service.get("version", "")
                        if service is not None
                        else "",
                    }
                )

                doc["ports"].append(port_data)

            docs.append(doc)

        return docs
    except Exception as e:
        print(f"[!] Erro ao processar {xml_path}: {e}")
        return []


def main(target_index: str) -> None:
    """Execução paralela dos scans"""
    output_index = f"{target_index}-portscan"
    ips = get_unique_ips(target_index)

    if not ips:
        print("[!] Nenhum IP válido encontrado")
        return

    print(f"[*] Iniciando scan de {len(ips)} IPs (Threads: {MAX_WORKERS})...")

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = {executor.submit(run_nmap, target_index, ip): ip for ip in ips}

        for future in as_completed(futures):
            ip = futures[future]
            try:
                xml_path = future.result()
                if not xml_path:
                    continue

                for doc in parse_nmap_results(xml_path, target_index):
                    client.index(index=output_index, body=doc, refresh=True)
                    print(f"[+] {ip} → {len(doc['ports'])} portas indexadas")

            except Exception as e:
                print(f"[!] Erro no IP {ip}: {e}")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(f"Uso: {sys.argv[0]} <indice_origem>")
        sys.exit(1)

    main(sys.argv[1])
