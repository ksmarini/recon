#!/usr/bin/env python3
import sys
import subprocess
from concurrent.futures import ProcessPoolExecutor, as_completed


def run_script(script_path, target, domain):
    try:
        cmd = ["python3", script_path, target, domain]
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        print(f"[✓] {script_path} executado com sucesso.")
        return result.stdout
    except subprocess.CalledProcessError as e:
        print(f"[!] Erro ao executar {script_path}:\n{e.stderr}")
        return None


def main():
    if len(sys.argv) != 3:
        print(f"Uso: {sys.argv[0]} <target> <domain>")
        sys.exit(1)

    target = sys.argv[1]
    domain = sys.argv[2]

    scripts = [
        "/home/marini/fontes/python/recon/auto_assetfinder.py",
        "/home/marini/fontes/python/recon/auto_subfinder.py",
        "/home/marini/fontes/python/recon/auto_sublist3r.py",
    ]

    print("[+] Iniciando execução paralela...")

    with ProcessPoolExecutor(max_workers=len(scripts)) as executor:
        futures = [
            executor.submit(run_script, script, target, domain) for script in scripts
        ]

        for future in as_completed(futures):
            output = future.result()
            if output:
                print(output)


if __name__ == "__main__":
    main()
