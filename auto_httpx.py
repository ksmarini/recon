#!/usr/bin/env python3
import sys
import argparse
import subprocess
import logging
from opensearchpy import OpenSearch
from datetime import datetime

# Configurar logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def get_opensearch_client():
    """Retorna um cliente configurado para o OpenSearch"""
    client = OpenSearch(
        hosts=[{"host": "localhost", "port": 9200}],
        http_compress=True,
        use_ssl=False,
        verify_certs=False,
        ssl_assert_hostname=False,
        ssl_show_warn=False,
    )
    return client


def get_unique_domains(index: str) -> list:
    """Recupera domínios únicos do índice OpenSearch"""
    client = get_opensearch_client()
    query = {
        "size": 0,
        "aggs": {
            "unique_domains": {
                "terms": {"field": "server.domain.keyword", "size": 10000}
            }
        },
    }

    try:
        response = client.search(index=index, body=query)
        domains = [
            bucket["key"]
            for bucket in response["aggregations"]["unique_domains"]["buckets"]
        ]
        logger.info(f"Encontrados {len(domains)} domínios únicos para verificação")
        return domains
    except Exception as e:
        logger.error(f"Falha ao buscar domínios: {str(e)}")
        return []


def check_domains_availability(target: str, domains: list) -> dict:
    """Verifica quais domínios estão disponíveis usando httpx"""
    if not domains:
        return {"available": [], "unavailable": []}

    # Preparar string com domínios (um por linha)
    domains_str = "\n".join(domains)
    container_name = f"{target}-httpx-check"

    # Comando para verificar domínios com httpx
    docker_cmd = f"docker run --rm --name {container_name} kali-tools:2.1 bash -c 'echo \"{domains_str}\" | httpx --silent'"

    try:
        logger.debug(f"Executando: {docker_cmd}")
        result = subprocess.run(
            docker_cmd,
            shell=True,
            check=True,
            timeout=600,  # 10 minutos
            capture_output=True,
            text=True,
        )

        # Processar saída (domínios disponíveis)
        available_domains = [
            domain.strip()
            for domain in result.stdout.strip().split("\n")
            if domain.strip()
        ]
        unavailable_domains = list(set(domains) - set(available_domains))

        logger.info(
            f"Verificação concluída: {len(available_domains)} domínios disponíveis, "
            f"{len(unavailable_domains)} indisponíveis"
        )

        return {"available": available_domains, "unavailable": unavailable_domains}

    except subprocess.TimeoutExpired:
        logger.warning(f"Timeout após 600s ao verificar domínios")
        return {"available": [], "unavailable": domains}
    except subprocess.CalledProcessError as e:
        logger.error(f"Erro ao executar httpx: {e.stderr}")
        return {"available": [], "unavailable": domains}
    except Exception as e:
        logger.error(f"Erro ao verificar domínios: {str(e)}")
        return {"available": [], "unavailable": domains}


def main():
    parser = argparse.ArgumentParser(
        description="Verificador de disponibilidade de domínios web"
    )
    parser.add_argument("target", help="Nome do alvo/cliente (índice no OpenSearch)")
    parser.add_argument(
        "--only-available",
        action="store_true",
        help="Exibir apenas domínios disponíveis",
    )
    parser.add_argument(
        "--only-unavailable",
        action="store_true",
        help="Exibir apenas domínios indisponíveis",
    )
    args = parser.parse_args()

    logger.info(f"Iniciando verificação de disponibilidade web para {args.target}")

    try:
        # Buscar domínios únicos
        domains = get_unique_domains(args.target)

        if not domains:
            print("Nenhum domínio encontrado no índice.")
            sys.exit(0)

        print(
            f"\nEncontrados {len(domains)} domínios únicos. Verificando disponibilidade...\n"
        )

        # Verificar disponibilidade
        results = check_domains_availability(args.target, domains)

        # Exibir resultados conforme solicitado
        if args.only_available:
            if results["available"]:
                print("\n=== DOMÍNIOS DISPONÍVEIS ===")
                for domain in sorted(results["available"]):
                    print(f"[+] {domain}")
            else:
                print("\nNenhum domínio disponível encontrado.")

        elif args.only_unavailable:
            if results["unavailable"]:
                print("\n=== DOMÍNIOS INDISPONÍVEIS ===")
                for domain in sorted(results["unavailable"]):
                    print(f"[-] {domain}")
            else:
                print("\nNenhum domínio indisponível encontrado.")

        else:
            # Exibir ambos
            if results["available"]:
                print("\n=== DOMÍNIOS DISPONÍVEIS ===")
                for domain in sorted(results["available"]):
                    print(f"[+] {domain}")

            if results["unavailable"]:
                print("\n=== DOMÍNIOS INDISPONÍVEIS ===")
                for domain in sorted(results["unavailable"]):
                    print(f"[-] {domain}")

        print(
            f"\nResumo: {len(results['available'])} disponíveis, {len(results['unavailable'])} indisponíveis"
        )

    except KeyboardInterrupt:
        logger.warning("Processo interrompido pelo usuário")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Erro crítico: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()
