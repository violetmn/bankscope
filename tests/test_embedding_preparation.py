from unittest.mock import patch
import numpy as np
from bankscope.store import Store
from bankscope.semantic import prepare


def test_inference_does_not_hold_write_lock_and_unchanged_vectors_are_reused(tmp_path):
    store=Store(str(tmp_path/'index.sqlite3'))
    try:
        store.add('DOC','Example',2023,'',['Financial statement page '+str(i) for i in range(40)],'hash')
        calls=[]
        class FakeModel:
            def __init__(self,*args,**kwargs):pass
            def passage_embed(self,texts,**kwargs):
                calls.append(len(texts))
                for text in texts:
                    assert not store.db.in_transaction
                    yield np.array([1.0,0.0],dtype=np.float32)
        with patch('fastembed.TextEmbedding',FakeModel):
            first=prepare(store)
            second=prepare(store)
        assert first['embedded_chunks']==40
        assert second['embedded_chunks']==0 and second['reused_chunks']==40
        assert calls==[40]
    finally:store.close()
