#!/usr/bin/env python3
import sys
import os
import json
import subprocess
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor
from typing import List, Dict

# Configuração de cores melhorada
COLORS = {
    "assetfinder": "\033[94m",  # Azul
    "subfinder": "\033[92m",  # Verde
    "sublist3r": "\033[93m",  # Amarelo
    "error": "\033[91m",  # Vermelho
    "header": "\033[95m",  # Magenta
    "reset": "\033[0m",
}


def get_tool_name(command: str) -> str:
    """Extrai o nome da ferramenta de forma segura"""
    base = os.path.basename(command)
    return base.replace("auto_", "").replace(".py", "")


def run_command(command: str) -> Dict:
    """Executa um comando com tratamento robusto de erros"""
    tool_name = get_tool_name(command.split()[1])
    try:
        result = subprocess.run(
            command.split(),
            check=True,
            capture_output=True,
            text=True,
            timeout=600,  # 10 minutos por ferramenta
        )
        return {"tool": tool_name, "output": result.stdout.splitlines(), "error": None}
    except Exception as e:
        return {
            "tool": tool_name,
            "output": [],
            "error": str(e.stderr) if hasattr(e, "stderr") else str(e),
        }


def print_colored_report(results: List[Dict]) -> None:
    """Exibe resultados com formatação avançada"""
    print(f"\n{COLORS['header']}🔍 RESULTADOS PARA O TARGET{COLORS['reset']}")

    for tool_data in results:
        color = COLORS.get(tool_data["tool"], COLORS["reset"])
        output = tool_data["output"] or ["Nenhum subdomínio encontrado"]

        # Cabeçalho
        print(f"\n{color}╔════════════════════════════════╗")
        print(f"║ {tool_data['tool'].upper():<28} ║")
        print(f"╚════════════════════════════════╝{COLORS['reset']}")

        # Subdomínios
        for sub in output:
            print(f"  {COLORS['reset']}• {sub}")

        # Erros
        if tool_data["error"]:
            print(f"\n{COLORS['error']}  ⚠ ERRO: {tool_data['error']}{COLORS['reset']}")


def save_raw_results(target: str, results: List[Dict]) -> None:
    """Salva resultados brutos mantendo duplicados"""
    output_dir = f"/docker/recon/data/{target}/subdomains"
    os.makedirs(output_dir, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    # Salvar por ferramenta
    for tool_data in results:
        tool_file = f"{output_dir}/{timestamp}_{tool_data['tool']}.txt"
        with open(tool_file, "w") as f:
            f.write("\n".join(tool_data["output"]))

    # Arquivo consolidado
    consolidated_file = f"{output_dir}/{timestamp}_consolidated.tsv"
    with open(consolidated_file, "w") as f:
        for tool_data in results:
            for sub in tool_data["output"]:
                f.write(f"{sub}\t{tool_data['tool']}\n")


def calculate_workers() -> int:
    """Calcula workers de forma segura"""
    cpu_count = os.cpu_count() or 4  # Default 4 se None
    return min(3, cpu_count * 2)  # Máximo 3 (1 por ferramenta)


def main(target: str, domain: str) -> None:
    commands = [
        f"python /home/marini/fontes/python/recon/auto_assetfinder.py {target} {domain}",
        f"python /home/marini/fontes/python/recon/auto_subfinder.py {target} {domain}",
        f"python /home/marini/fontes/python/recon/auto_sublist3r.py {target} {domain}",
    ]

    workers = calculate_workers()

    print(f"{COLORS['header']}\n🚀 Iniciando recon para: {domain}")
    print(f"⚡ Workers: {workers}{COLORS['reset']}\n")

    with ThreadPoolExecutor(max_workers=workers) as executor:
        results = list(executor.map(run_command, commands))

    print_colored_report(results)
    save_raw_results(target, results)

    # Resumo final
    total = sum(len(tool["output"]) for tool in results)
    print(
        f"\n{COLORS['header']}✅ Finalizado! Total de subdomínios: {total}{COLORS['reset']}"
    )
    for tool in results:
        print(
            f"  {COLORS[tool['tool']]}• {tool['tool'].upper()}: {len(tool['output'])}"
        )


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print(f"Uso: {sys.argv[0]} <target> <domain>")
        sys.exit(1)

    main(sys.argv[1], sys.argv[2])
