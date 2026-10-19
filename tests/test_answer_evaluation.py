import json
import pytest
from bankscope.answer_evaluation import DIMENSIONS, preflight, execute, score
from bankscope.store import Store


def pilot(tmp_path):
    s=Store(tmp_path/'index.db');s.add('BANK','Bank',2023,'',['Deposits were 100 million'], 'abc')
    q=tmp_path/'questions.jsonl'
    q.write_text(json.dumps({'id':'q1','split':'development','doc_name':'BANK','question':'What were deposits?',
                             'answer':'GOLD_SECRET_LABEL','expected_behavior':'answer_from_evidence'})+'\n')
    return s,q


def test_plan_does_not_leak_labels(tmp_path):
    s,q=pilot(tmp_path)
    try:
        plan=preflight(s,q)
        assert 'GOLD_SECRET_LABEL' not in json.dumps(plan)
        assert 'expected_behavior' not in json.dumps(plan)
        assert plan['paid_calls']==0
        assert plan['estimated_upper_cost_usd']>0
    finally:s.close()


@pytest.mark.parametrize('change',[{'split':'reserved_test'},{'doc_name':'MISSING'}])
def test_unready_questions_rejected(tmp_path,change):
    s,q=pilot(tmp_path)
    row=json.loads(q.read_text());row.update(change);q.write_text(json.dumps(row))
    try:
        with pytest.raises(ValueError):preflight(s,q)
    finally:s.close()


def test_budget_prevents_calls_and_existing_output(tmp_path,monkeypatch):
    s,q=pilot(tmp_path)
    try:p=preflight(s,q)
    finally:s.close()
    plan=tmp_path/'plan.json';plan.write_text(json.dumps(p))
    def forbidden(*a,**k):raise AssertionError('Provider must not be called')
    monkeypatch.setattr('bankscope.answer_evaluation.generate',forbidden)
    with pytest.raises(ValueError):execute(plan,tmp_path/'out',0)
    with pytest.raises(FileExistsError):execute(plan,tmp_path,1)


def test_mock_generation_creates_unscored_reviews(tmp_path,monkeypatch):
    s,q=pilot(tmp_path)
    try:p=preflight(s,q)
    finally:s.close()
    plan=tmp_path/'plan.json';plan.write_text(json.dumps(p))
    monkeypatch.setattr('bankscope.answer_evaluation.generate',lambda *a,**k:{'status':'generated_unverified_claims','answer':'100 million [S1]'})
    dest=tmp_path/'out';execute(plan,dest,1)
    assert json.loads((dest/'run.json').read_text())['complete']
    with pytest.raises(ValueError):score(dest/'reviews.jsonl',['q1'])


def test_scoring_requires_review_and_handles_na(tmp_path):
    p=tmp_path/'review.jsonl'
    row={'id':'q1','reviewer':'Independent reviewer','reference_verified':True,'notes':'Checked source page',**{d:2 for d in DIMENSIONS}}
    row['abstention']='n/a';p.write_text(json.dumps(row))
    result=score(p,['q1'])
    assert result['dimensions']['correctness']['mean_out_of_two']==2
    assert result['dimensions']['abstention']['mean_out_of_two'] is None
    with pytest.raises(ValueError):score(p,['q1','missing'])
    row['correctness']=True;p.write_text(json.dumps(row))
    with pytest.raises(ValueError):score(p,['q1'])


def test_provider_failure_preserves_partial_review_artifacts(tmp_path,monkeypatch):
    s,q=pilot(tmp_path)
    try:p=preflight(s,q)
    finally:s.close()
    plan=tmp_path/'plan.json';plan.write_text(json.dumps(p))
    def failed(*a,**k):raise ValueError('Paid generation is disabled')
    monkeypatch.setattr('bankscope.answer_evaluation.generate',failed)
    dest=tmp_path/'out';execute(plan,dest,1)
    assert json.loads((dest/'answers.jsonl').read_text())['response']['status']=='provider_error'
    assert (dest/'reviews.jsonl').exists()
