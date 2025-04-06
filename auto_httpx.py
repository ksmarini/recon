# get_subdomains.py
import argparse
from conn.database import get_opensearch_client


def get_subdomains(index_name):
    """Retorna uma lista de subdomínios únicos do campo 'server.domain' no OpenSearch.

    Args:
        index_name (str): Nome do índice onde os dados estão armazenados.
    """
    client = None
    try:
        client = get_opensearch_client()

        query = {
            "size": 0,
            "aggs": {
                "unique_subdomains": {
                    "terms": {"field": "server.domain.keyword", "size": 10000}
                }
            },
        }

        # Usa o índice passado como argumento
        response = client.search(index=index_name, body=query)

        buckets = (
            response.get("aggregations", {})
            .get("unique_subdomains", {})
            .get("buckets", [])
        )
        subdomains = [bucket["key"] for bucket in buckets if "key" in bucket]

        return subdomains

    except Exception as e:
        print(f"Erro ao buscar subdomínios: {e}")
        return []
    finally:
        if client:
            client.close()


if __name__ == "__main__":
    # Configura o parser de argumentos
    parser = argparse.ArgumentParser(description="Busca subdomínios no OpenSearch")
    parser.add_argument(
        "--index", required=True, help="Nome do índice OpenSearch (ex: pmro)"
    )
    args = parser.parse_args()

    # Executa a busca com o índice fornecido
    subdomains = get_subdomains(args.index)

    print("Subdomínios encontrados:")
    for subdomain in subdomains:
        print(subdomain)
