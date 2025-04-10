#!/usr/bin/env python3
import sys
import os
import subprocess
import argparse
import uuid
import time
from typing import List, Dict, Generator, Set
from datetime import datetime
from opensearchpy import OpenSearch
from tqdm import tqdm
from colorama import Fore, Style, init

# Inicializar colorama (necessário para Windows)
init()


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


def get_unique_domains(index: str) -> List[str]:
    """
    Recupera domínios únicos do índice OpenSearch

    Args:
        index: Nome do índice a consultar

    Returns:
        List[str]: Lista de domínios únicos
    """
    print(
        f"{Fore.CYAN}[*] Consultando domínios únicos no índice {index}...{Style.RESET_ALL}"
    )
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
        print(
            f"{Fore.CYAN}[*] Encontrados {len(domains)} domínios únicos para verificação{Style.RESET_ALL}"
        )
        return domains
    except Exception as e:
        print(f"{Fore.RED}[!] Falha ao buscar domínios: {str(e)}{Style.RESET_ALL}")
        return []


def criar_diretorios(target: str) -> str:
    """
    Cria os diretórios necessários para o alvo

    Args:
        target: Nome do alvo/cliente

    Returns:
        str: Caminho do diretório temp
    """
    temp_dir = f"/docker/recon/data/{target}/temp"
    try:
        os.makedirs(temp_dir, exist_ok=True)
        return temp_dir
    except Exception as e:
        print(f"{Fore.RED}[!] Erro ao criar diretórios: {str(e)}{Style.RESET_ALL}")
        sys.exit(1)


def check_domains_availability_in_batches(
    target: str, domains: List[str], batch_size: int = 20
) -> Generator[Dict, None, None]:
    """
    Verifica quais domínios estão disponíveis usando httpx, processando em lotes
    e retornando resultados progressivamente

    Args:
        target: Nome do alvo/cliente
        domains: Lista de domínios a verificar
        batch_size: Tamanho de cada lote para processamento

    Yields:
        Dict: Informações sobre cada domínio processado
    """
    if not domains:
        return

    temp_dir = criar_diretorios(target)
    total_domains = len(domains)

    # Preparar arquivo para salvar resultados
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    results_file = f"{temp_dir}/httpx-results-{timestamp}.txt"

    # Dividir domínios em lotes para processamento
    batches = [domains[i : i + batch_size] for i in range(0, len(domains), batch_size)]

    with tqdm(total=total_domains, desc="Verificando domínios") as pbar:
        for batch_idx, batch in enumerate(batches):
            batch_str = "\n".join(batch)
            scan_id = str(uuid.uuid4())[:8]
            container_name = f"{target}-httpx-{scan_id}"

            # Criar arquivo temporário para este lote
            batch_file = f"{temp_dir}/httpx-batch-{batch_idx}.txt"
            with open(batch_file, "w") as f:
                f.write(batch_str)

            # Comando para verificar domínios com httpx
            cmd = (
                f"docker run --rm --name {container_name} "
                f"-v {temp_dir}:/data kali-tools:2.1 "
                f"bash -c 'cat /data/httpx-batch-{batch_idx}.txt | "
                f"httpx --silent --status-code --title --tech-detect'"
            )

            try:
                result = subprocess.run(
                    cmd,
                    shell=True,
                    check=True,
                    capture_output=True,
                    text=True,
                    timeout=180,  # 3 minutos por lote
                )

                # Limpar o arquivo de lote
                os.remove(batch_file)

                # Processar resultados deste lote
                output_lines = result.stdout.strip().split("\n")
                available_domains = set()

                for line in output_lines:
                    if line.strip():
                        # httpx output pode incluir status code, título e tecnologias
                        # Formato típico: http://example.com [200] [Example Title] [tech1,tech2]
                        parts = line.split()
                        if parts:
                            domain = parts[0]
                            status_info = " ".join(parts[1:]) if len(parts) > 1 else ""

                            # Extrair apenas o nome do domínio da URL
                            domain_clean = domain.replace("http://", "").replace(
                                "https://", ""
                            )
                            domain_clean = domain_clean.split("/")[0]  # Remover path

                            available_domains.add(domain_clean)

                            # Adicionar ao arquivo de resultados
                            with open(results_file, "a") as f:
                                f.write(f"{line}\n")

                            # Retornar este resultado imediatamente
                            yield {
                                "domain": domain_clean,
                                "full_url": domain,
                                "status": "available",
                                "details": status_info,
                            }

                # Processar domínios indisponíveis neste lote
                for domain in batch:
                    domain_clean = domain.split("/")[
                        0
                    ]  # Garantir que estamos comparando apenas o nome do domínio
                    if domain_clean not in available_domains:
                        yield {
                            "domain": domain_clean,
                            "status": "unavailable",
                            "details": "",
                        }

                # Atualizar barra de progresso
                pbar.update(len(batch))

            except subprocess.TimeoutExpired:
                print(
                    f"{Fore.YELLOW}[!] Timeout ao processar lote {batch_idx + 1}/{len(batches)}{Style.RESET_ALL}"
                )
                # Marcar todos os domínios do lote como indisponíveis
                for domain in batch:
                    yield {"domain": domain, "status": "error", "details": "Timeout"}
                pbar.update(len(batch))

            except Exception as e:
                print(
                    f"{Fore.RED}[!] Erro ao processar lote {batch_idx + 1}/{len(batches)}: {str(e)}{Style.RESET_ALL}"
                )
                # Marcar todos os domínios do lote como erro
                for domain in batch:
                    yield {"domain": domain, "status": "error", "details": str(e)}
                pbar.update(len(batch))

            # Pequena pausa entre lotes para não sobrecarregar o Docker
            time.sleep(1)

    print(
        f"{Fore.CYAN}[*] Resultados detalhados salvos em: {results_file}{Style.RESET_ALL}"
    )


def main():
    parser = argparse.ArgumentParser(
        description="Verificador de disponibilidade web de domínios"
    )
    parser.add_argument("target", help="Nome do índice/alvo no OpenSearch")
    parser.add_argument(
        "--batch-size",
        type=int,
        default=20,
        help="Número de domínios a processar por lote (default: 20)",
    )
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

    start_time = time.time()
    print(
        f"{Fore.CYAN}[*] Iniciando verificação de disponibilidade web para {args.target}{Style.RESET_ALL}"
    )

    try:
        # Buscar domínios únicos
        domains = get_unique_domains(args.target)

        if not domains:
            print(
                f"{Fore.YELLOW}[!] Nenhum domínio encontrado no índice {args.target}{Style.RESET_ALL}"
            )
            sys.exit(0)

        # Para armazenar os domínios classificados
        available_domains: Set[str] = set()
        unavailable_domains: Set[str] = set()
        error_domains: Set[str] = set()

        # Informações detalhadas por domínio
        domain_details = {}

        # Verificar disponibilidade com feedback progressivo
        print(
            f"\n{Fore.CYAN}[*] Iniciando verificação de {len(domains)} domínios...{Style.RESET_ALL}\n"
        )

        for result in check_domains_availability_in_batches(
            args.target, domains, args.batch_size
        ):
            domain = result["domain"]
            status = result["status"]
            domain_details[domain] = result.get("details", "")

            if status == "available":
                available_domains.add(domain)
                if not args.only_unavailable:
                    details = (
                        f" - {domain_details[domain]}" if domain_details[domain] else ""
                    )
                    print(f"{Fore.GREEN}[+] {domain}{details}{Style.RESET_ALL}")
            elif status == "unavailable":
                unavailable_domains.add(domain)
                if not args.only_available:
                    print(f"{Fore.RED}[-] {domain}{Style.RESET_ALL}")
            else:  # error
                error_domains.add(domain)
                if not args.only_available:
                    print(
                        f"{Fore.YELLOW}[!] {domain} - {domain_details[domain]}{Style.RESET_ALL}"
                    )

        # Resumo final
        elapsed_time = time.time() - start_time
        print(f"\n{Fore.CYAN}{'=' * 50}{Style.RESET_ALL}")
        print(f"{Fore.CYAN}RESUMO DE RESULTADOS:{Style.RESET_ALL}")
        print(
            f"{Fore.GREEN}[+] Domínios disponíveis: {len(available_domains)}{Style.RESET_ALL}"
        )
        print(
            f"{Fore.RED}[-] Domínios indisponíveis: {len(unavailable_domains)}{Style.RESET_ALL}"
        )
        if error_domains:
            print(
                f"{Fore.YELLOW}[!] Domínios com erro: {len(error_domains)}{Style.RESET_ALL}"
            )
        print(
            f"{Fore.CYAN}[*] Tempo total: {elapsed_time:.2f} segundos{Style.RESET_ALL}"
        )
        print(f"{Fore.CYAN}{'=' * 50}{Style.RESET_ALL}")

    except KeyboardInterrupt:
        print(f"\n{Fore.YELLOW}[!] Processo interrompido pelo usuário{Style.RESET_ALL}")
        elapsed_time = time.time() - start_time
        print(
            f"{Fore.CYAN}[*] Tempo decorrido: {elapsed_time:.2f} segundos{Style.RESET_ALL}"
        )
        sys.exit(1)
    except Exception as e:
        print(f"\n{Fore.RED}[!] Erro crítico: {str(e)}{Style.RESET_ALL}")
        sys.exit(1)


if __name__ == "__main__":
    main()
