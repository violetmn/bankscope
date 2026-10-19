import importlib.util
import json
from pathlib import Path
import pytest


def load(name):
    spec=importlib.util.spec_from_file_location(name,Path(__file__).parents[1]/'scripts'/f'{name}.py')
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module


def test_candidate_readiness_refuses_unmapped_or_overlapping_issuers(tmp_path):
    audit=load('audit_benchmark').audit
    path=tmp_path/'questions.jsonl'
    rows=[{'id':'1','company':'Bank','split':'development'},
          {'id':'2','company':'BANK','split':'reserved_test'}]
    path.write_text(''.join(json.dumps(r)+'\n' for r in rows))
    result=audit(path)
    assert result['ready'] is False
    assert result['mapping_or_review_pending']==2
    assert result['issuer_split_overlap']==['bank']
    rows[1]['id']='1';path.write_text(''.join(json.dumps(r)+'\n' for r in rows))
    with pytest.raises(ValueError):audit(path)


def test_finrag_import_preserves_issuer_split_and_flags_missing_sources(tmp_path,monkeypatch):
    module=load('prepare_finrag')
    source=tmp_path/'source.xlsx';source.write_bytes(b'fixture')
    def row(bank):return {'Bank':bank,'Query':'What is capital?','Value':'12.5',
                          'Year':'2023.0','Source Document Year':'2023.0',
                          'Doc Type':'Report','Data':'Capital','Numerical':'Y','In table':'Y'}
    monkeypatch.setattr(module,'read_rows',lambda path:[row('JP Morgan'),row('Other bank')])
    target=tmp_path/'output';module.prepare(source,target)
    rows=[json.loads(x) for x in (target/'candidates.jsonl').read_text().splitlines()]
    assert next(r for r in rows if r['company']=='JP Morgan')['split']=='development'
    assert all(r['mapping_status']=='report_and_page_required' for r in rows)
    assert json.loads((target/'manifest.json').read_text())['ready_for_evaluation'] is False
