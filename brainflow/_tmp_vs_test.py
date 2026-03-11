from core.vector_store import LocalVectorStore

vs = LocalVectorStore('memory/vector_store/test.sqlite')
vs.upsert('x', 'hello world', doc_type='test')
print(vs.search('hello', top_k=1)[0]['id'])
