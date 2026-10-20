import hashlib
import pytest
from bankscope.store import Store
from bankscope.page_contexts import prepare


def test_backfill_preserves_vectors_tables_and_chunks(tmp_path,monkeypatch):
    import pypdfium2
    path=tmp_path/'report.pdf';path.write_bytes(b'%PDF-source-bytes')
    s=Store(tmp_path/'db.sqlite3')
    try:
        s.add('D','Example',2024,'',['Original indexed passage'],hashlib.sha256(path.read_bytes()).hexdigest())
        s.db.execute('delete from page_contexts')
        s.db.execute('insert into embeddings values(?,?,?,?)',('D:p1:c0','model','sha',b'vector'))
        s.db.execute('insert into report_tables values(?,?,?)',('D','checked','{}'));s.db.commit()
        before={t:[tuple(x) for x in s.db.execute('select * from '+t)] for t in ['passages','embeddings','report_tables']}
        closed=[]
        class Text:
            def get_text_bounded(self):return 'Financial Highlights\n2024 2023\nNet income 77 66'
            def close(self):closed.append('text')
        class Page:
            def get_textpage(self):return Text()
            def close(self):closed.append('page')
        class PDF:
            def __enter__(self):return self
            def __exit__(self,*args):pass
            def __len__(self):return 1
            def __getitem__(self,i):return Page()
        monkeypatch.setattr('bankscope.page_contexts.report_path',lambda _:path)
        monkeypatch.setattr(pypdfium2,'PdfDocument',lambda _:PDF())
        assert prepare(s)['prepared_reports']==['D']
        assert '\n2024 2023\n' in s.db.execute('select text from page_contexts').fetchone()[0]
        assert closed==['text','page']
        assert prepare(s)['prepared_reports']==[]
        for t,rows in before.items():assert [tuple(x) for x in s.db.execute('select * from '+t)]==rows
    finally:s.close()


@pytest.mark.parametrize('available',[False,True])
def test_backfill_rejects_missing_or_changed_source(tmp_path,monkeypatch,available):
    path=tmp_path/'changed.pdf';path.write_bytes(b'%PDF-changed')
    s=Store(tmp_path/'db.sqlite3')
    try:
        s.add('D','Example',2024,'',['Page'],'original-hash')
        s.db.execute('delete from page_contexts');s.db.commit()
        monkeypatch.setattr('bankscope.page_contexts.report_path',lambda _:path if available else None)
        with pytest.raises(ValueError,match='differs|unavailable'):prepare(s)
        assert s.db.execute('select count(*) from page_contexts').fetchone()[0]==0
    finally:s.close()
