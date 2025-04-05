#!/usr/bin/env python3
import sys
import os
import subprocess
from concurrent.futures import ThreadPoolExecutor, as_completed

# Configurações de performance
MAX_WORKERS = min(4, (os.cpu_count() or 2))  # Balanceamento CPU/memória
TIMEOUT_PER_SCRIPT = 300  # 5 minutos por ferramenta
SCRIPTS = [
    "/home/marini/fontes/python/recon/auto_assetfinder.py",
    "/home/marini/fontes/python/recon/auto_subfinder.py",
    "/home/marini/fontes/python/recon/auto_sublist3r.py",
]


def run_tool(script: str, target: str, domain: str) -> None:
    """Executa uma ferramenta e exibe resultados imediatamente"""
    try:
        with subprocess.Popen(
            ["python3", script, target, domain],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,
        ) as proc:
            # Processa output em tempo real
            for line in proc.stdout:
                print(f"[{os.path.basename(script)[5:-3]}] {line.strip()}")

            # Verifica erros após conclusão
            if proc.wait() != 0:
                raise subprocess.CalledProcessError(
                    proc.returncode, proc.args, stderr=proc.stderr.read()
                )

    except Exception as e:
        print(f"ERRO em {script}: {str(e)[:100]}")


def main(target: str, domain: str) -> None:
    """Execução principal otimizada"""
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = {
            executor.submit(run_tool, script, target, domain): script
            for script in SCRIPTS
        }

        try:
            for future in as_completed(futures, timeout=TIMEOUT_PER_SCRIPT + 10):
                future.result()  # Apenas para capturar exceções
        except Exception as e:
            print(f"Timeout ou erro crítico: {e}")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print(f"Uso: {sys.argv[0]} <target> <domain>")
        sys.exit(1)

    main(sys.argv[1], sys.argv[2])
