#!/usr/bin/env python3
import sys
from conn.database import get_opensearch_client


def consultar_indice_sem_duplicados(index_name):
    client = get_opensearch_client()

    query = {
        "size": 0,
        "aggs": {
            "dominios_unicos": {
                "terms": {
                    "field": "server.domain.keyword",
                    "size": 10000,
                    "order": {"_key": "asc"},  # Ordenação alfabética
                }
            }
        },
    }

    try:
        response = client.search(index=index_name, body=query)
        buckets = response["aggregations"]["dominios_unicos"]["buckets"]

        if not buckets:
            print("Nenhum resultado encontrado.")
            return

        # Imprime os resultados ordenados
        total = 0
        for item in buckets:
            print(item["key"])
            total += 1

        print(f"\nTotal de registros únicos: {total}")

    except Exception as e:
        print(f"Erro na consulta: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(f"Uso: {sys.argv[0]} <nome-do-indice>")
        sys.exit(1)

    consultar_indice_sem_duplicados(sys.argv[1])
