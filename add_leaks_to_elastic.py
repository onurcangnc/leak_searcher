from elasticsearch import Elasticsearch, helpers
import os

# Elasticsearch bağlantısı
es = Elasticsearch("http://localhost:9200")

# Belirttiğiniz dosyaların listesi
files_to_upload = [
    r"C:/Users/Onurcan/Desktop/Pentest/Leak/example_leak2.txt",
    r"C:/Users/Onurcan/Desktop/Pentest/Leak/example_leak1.txt",
    r"C:/Users/Onurcan/Desktop/Pentest/Leak/example_leak3.txt",
    r"C:/Users/Onurcan/Desktop/Pentest/Leak/example_leak4.txt",
    r"C:/Users/Onurcan/Desktop/Pentest/Leak/example_leak5.txt",
    r"C:/Users/Onurcan/Desktop/Pentest/Leak/example_leak6.txt",
    r"C:/Users/Onurcan/Desktop/Pentest/Leak/example_leak7.txt"
]

def ensure_index_mapping(index_name):
    """
    Eğer indeks mevcutsa siler ve yeniden oluşturur. Mapping sadece 'content' ve 'line_number' alanlarını içerir.
    """
    if es.indices.exists(index=index_name):
        es.indices.delete(index=index_name)
        print(f"Index '{index_name}' silindi.")

    es.indices.create(index=index_name, body={
        "mappings": {
            "properties": {
                "content": {
                    "type": "text"
                },
                "line_number": {
                    "type": "integer"
                }
            }
        }
    })
    print(f"Index '{index_name}' oluşturuldu.")

def bulk_index_file(file_path, index_name):
    """
    Belirtilen dosyayı Elasticsearch'e satır bazında indeksler.
    :param file_path: Yüklenecek dosyanın tam yolu
    :param index_name: Elasticsearch'te kullanılacak indeks adı
    """
    actions = []
    with open(file_path, 'r', encoding='utf-8') as file:
        for line_number, line in enumerate(file, start=1):
            content = line.strip()
            if not content:  # Boş satırları atla
                continue

            actions.append({
                "_index": index_name,
                "_id": f"{os.path.basename(file_path)}_{line_number}",
                "_source": {
                    "content": content,
                    "line_number": line_number
                }
            })

            # Her 1000 belgeyi topluca yükle
            if len(actions) >= 1000:
                helpers.bulk(es, actions)
                actions = []

        # Kalan belgeleri yükle
        if actions:
            helpers.bulk(es, actions)

    print(f"Dosya '{file_path}' başarıyla indekslendi.")

def delete_all_indices():
    """
    Elasticsearch'teki tüm indeksleri siler.
    """
    indices = es.indices.get_alias(index="*")
    for index_name in indices.keys():
        es.indices.delete(index=index_name)
        print(f"Index '{index_name}' silindi.")

# Belirtilen dosyaları yükleme işlemi
for file_path in files_to_upload:
    index_name = os.path.basename(file_path).replace(".txt", "").lower()
    ensure_index_mapping(index_name)  # İndeks mapping kontrolü ve yeniden oluşturma
    print(f"Uploading {file_path} to index {index_name}...")
    bulk_index_file(file_path, index_name)  # Dosyayı yükle
    print(f"Finished uploading {file_path} to index {index_name}.")

# Tüm indeksleri silmek için fonksiyonu çağırabilirsiniz
# delete_all_indices()
