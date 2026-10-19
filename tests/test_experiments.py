import json
import pytest
from bankscope.store import Store
from bankscope.experiments import run, fingerprint, markdown


def fixture(tmp_path):
    s=Store(tmp_path/'index.db')
    s.add('BANK','Bank',2023,'https://example.test',['Customer deposits increased'], 'abc')
    q=tmp_path/'questions.jsonl'
    q.write_text(json.dumps({'id':'q1','doc_name':'BANK','question':'customer deposits',
                            'evidence':[{'evidence_page_num':0}]})+'\n')
    return s,q


def test_reproducible_run_with_provenance_and_trace(tmp_path):
    s,q=fixture(tmp_path)
    try:
        result=run(s,q)
        assert result['paid_calls']==0
        assert len(result['questions_sha256'])==64
        assert result['corpus_passages_sha256']==fingerprint(s)
        for row in result['results']:
            assert row['identical_rankings']
            assert row['runs'][0]['metrics']['hit_rate']==1
            assert row['runs'][0]['trace'][0]['pages']==[['BANK',1]]
        assert '1.000' in markdown(result)
        old=fingerprint(s)
        s.add('OTHER','Other',2022,'',['different text'],'def')
        assert fingerprint(s)!=old
    finally:
        s.close()


@pytest.mark.parametrize('kwargs',[{'repeats':0},{'repeats':11},{'strategies':['invalid']},{'modes':['invalid']}])
def test_invalid_experiment_config(tmp_path,kwargs):
    s,q=fixture(tmp_path)
    try:
        with pytest.raises(ValueError):
            run(s,q,**kwargs)
    finally:
        s.close()
