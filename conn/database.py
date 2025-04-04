# database.py
from opensearchpy import OpenSearch


def get_opensearch_client():
    """Retorna o cliente OpenSearch configurado."""
    host = "localhost"
    port = 9200

    client = OpenSearch(
        hosts=[{"host": host, "port": port}],
        http_compress=True,
        use_ssl=False,
        verify_certs=False,
        ssl_assert_hostname=False,
        ssl_show_warn=False,
    )

    return client
