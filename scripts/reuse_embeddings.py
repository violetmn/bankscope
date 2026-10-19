"""Reuse only identical text/model vectors across local benchmark indexes."""
import argparse
import hashlib
from bankscope.semantic import MODEL
from bankscope.store import Store


def reuse(source, destination):
    a,b=Store(source),Store(destination)
    try:
        vectors={r['text_sha256']:r['vector'] for r in a.db.execute('SELECT text_sha256,vector FROM embeddings WHERE model=?',(MODEL,))}
        records=[]
        for row in b.db.execute('SELECT chunk_id,text FROM passages'):
            digest=hashlib.sha256(row['text'].encode()).hexdigest()
            if digest in vectors:records.append((row['chunk_id'],MODEL,digest,vectors[digest]))
        with b.db:b.db.executemany('INSERT OR REPLACE INTO embeddings VALUES(?,?,?,?)',records)
        return len(records)
    finally:a.close();b.close()


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--source',required=True);p.add_argument('--destination',required=True);a=p.parse_args()
    print('Reused identical cached vectors:',reuse(a.source,a.destination))
