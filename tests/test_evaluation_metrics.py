import json
import math
import pytest
from bankscope.evaluation import evaluate


class RankedStore:
    def __init__(self):
        self.search_arguments=[]

    def documents(self):
        return [{'id':'A'},{'id':'B'}]

    def search(self,question,**kwargs):
        self.search_arguments.append((question,kwargs))
        return [{'doc_id':'A','page':9},{'doc_id':'A','page':2},
                {'doc_id':'A','page':2},{'doc_id':'B','page':3}][:kwargs['k']]


def question_file(tmp_path,records):
    p=tmp_path/'questions.jsonl'
    p.write_text('\n'.join(json.dumps(r) for r in records))
    return p


def record():
    return {'financebench_id':'q1','doc_name':'A','question':'Find deposits',
            'answer':'GOLD NEVER SEARCHED','evidence':[
                {'doc_name':'A','evidence_page_num':1},
                {'doc_name':'B','evidence_page_num':2}]}


def test_hand_computed_metrics_and_duplicate_page_credit(tmp_path):
    store=RankedStore()
    p=question_file(tmp_path,[record()])
    result=evaluate(store,p,k=4)
    assert result['hit_rate']==1
    assert result['mrr']==0.5
    assert result['page_recall']==1
    expected=(1/math.log2(3)+1/math.log2(5))/(1+1/math.log2(3))
    assert result['ndcg']==pytest.approx(expected)
    assert store.search_arguments==[('Find deposits',{'k':4,'doc_id':'A','strategy':'bm25'})]


def test_corpus_evaluation_does_not_supply_gold_document_filter(tmp_path):
    store=RankedStore()
    evaluate(store,question_file(tmp_path,[record()]),mode='corpus')
    assert store.search_arguments[0][1]['doc_id'] is None


def test_zero_eligible_samples_are_not_reported_as_zero_accuracy(tmp_path):
    q=record();q['evidence']=[{'doc_name':'missing','evidence_page_num':0}]
    result=evaluate(RankedStore(),question_file(tmp_path,[q]))
    assert result['evaluated']==0 and result['hit_rate'] is None
    assert result['skipped_missing_documents']==1


@pytest.mark.parametrize('k',[0,-1,21])
def test_invalid_k_rejected_even_with_no_questions(tmp_path,k):
    with pytest.raises(ValueError):
        evaluate(RankedStore(),question_file(tmp_path,[]),k=k)
