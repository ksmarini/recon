import sys
import subprocess

domain = sys.argv[1]

try:
    result = subprocess.run(
        f"docker run --rm --name teste kali-tools:2.1 subfinder -d {domain}",
        shell=True,
        check=True,
        capture_output=True,
        text=True,
    )

    # quebra a saída em linhas únicas, remove duplicatas
    lista = sorted(set(result.stdout.splitlines()))

    # imprime a lista esperada pela automação
    print(lista)

    # # imprime um item por linha para teste humanizado
    # for item in lista:
    #     print(item)

except subprocess.CalledProcessError as e:
    print("Erro ao executar o comando:")
    print("STDOUT:", e.stdout)
    print("STDERR:", e.stderr)
    print("Código de saída:", e.returncode)
