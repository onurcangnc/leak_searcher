# elastic_manager.py

from elasticsearch import Elasticsearch, exceptions
import logging
import os

# Logging Ayarları
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ElasticManager:
    def __init__(self, host="http://localhost:9200", username=None, password=None):
        try:
            if username and password:
                self.client = Elasticsearch(hosts=[host], basic_auth=(username, password))
            else:
                self.client = Elasticsearch(hosts=[host])
            # Bağlantıyı test et
            if not self.client.ping():
                raise ValueError("Elasticsearch sunucusuna bağlanılamadı.")
            logger.info("Elasticsearch bağlantısı başarılı.")
        except exceptions.ConnectionError as ce:
            logger.error(f"Elasticsearch bağlantı hatası: {ce}")
            raise
        except Exception as e:
            logger.error(f"Elasticsearch başlatılırken hata oluştu: {e}")
            raise

    def list_indices(self):
        """Elasticsearch'teki tüm indeksleri listele."""
        try:
            indices = self.client.indices.get_alias(index="*")
            index_list = list(indices.keys())
            logger.info(f"Mevcut indeksler: {index_list}")
            return index_list
        except Exception as e:
            logger.error(f"Indeks listelenirken hata: {e}")
            return []

    def search_documents(self, index_name, query, size=10):
        """
        Elasticsearch'te belirtilen sorguyu çalıştırır.
        :param index_name: Arama yapılacak indeks adı
        :param query: Elasticsearch sorgusu
        :param size: Döndürülecek maksimum sonuç sayısı
        """
        try:
            response = self.client.search(index=index_name, query=query, size=size)
            logger.info(f"Arama yapıldı: {query}")
            return response['hits']['hits']
        except Exception as e:
            logger.error(f"Arama yapılırken hata: {e}")
        return []

