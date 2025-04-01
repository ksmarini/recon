import json


def parse_nuclei_json():
    with open("/home/marini/pentest/pm.ro.gov.br/nuclei.json") as file:
        for line in file:
            line = line.strip()
            if not line:
                continue

            try:
                entry = json.loads(line)

                # Construir o dicionário com tratamento de campos ausentes
                parsed_data = {
                    "template": entry.get("template-id", ""),
                    "name": entry.get("info", {}).get("name", ""),
                    "severity": entry.get("info", {}).get("severity", ""),
                    "tags": ", ".join(entry.get("info", {}).get("tags", [])),
                    "host": entry.get("host", ""),
                    "type": entry.get("type", ""),
                    "matched": entry.get("matched-at", ""),
                    "extracted_results": ", ".join(
                        entry.get("extracted-results", [])
                    ),  # Trata lista
                    "ip": entry.get("ip", ""),
                    # "curl_command": entry.get("curl-command", ""),  # Campo adicional
                }

                print(parsed_data)

            except json.JSONDecodeError:
                print(f"Erro ao decodificar linha: {line}")
            except Exception as e:
                print(f"Erro inesperado: {e}")


def main():
    parse_nuclei_json()


if __name__ == "__main__":
    main()
