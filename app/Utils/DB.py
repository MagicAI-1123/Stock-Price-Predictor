import hashlib

def generate_news_hash(news_item):
    data = f"{news_item['stockName']}-{news_item['headlineInfo']}"
    return hashlib.md5(data.encode('utf-8')).hexdigest()
