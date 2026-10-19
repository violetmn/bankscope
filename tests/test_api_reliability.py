from unittest.mock import patch
import pytest
from fastapi.testclient import TestClient
from bankscope.api import app
from bankscope.store import Store


@pytest.fixture
def client(tmp_path):
    path=str(tmp_path/'index.sqlite3')
    store=Store(path)
    store.add('BANK_2022','Bank',2022,'https://example.org/report.pdf',['Customer deposits were $50 million in 2022.'],'hash')
    store.close()
    with patch('bankscope.api.Store',side_effect=lambda:Store(path)):
        yield TestClient(app)


@pytest.mark.parametrize('question',['   ','\n\t   ','!!!','a','x'*2001])
def test_bad_questions_rejected_before_search_or_payment(client,question):
    with patch('bankscope.api.generate') as provider:
        result=client.post('/query',json={'question':question,'generate_answer':True})
    assert result.status_code==422
    provider.assert_not_called()


def test_unknown_year_gives_no_evidence(client):
    result=client.post('/query',json={'question':'Customer deposits','company':'Bank','year':2025})
    assert result.status_code==200
    assert result.json()['sources']==[]


def test_real_pipeline_mock_provider_exposes_numeric_warning(client,tmp_path,monkeypatch):
    from bankscope.generation import generate
    monkeypatch.setenv('BANKSCOPE_ENABLE_PAID','1')
    monkeypatch.setenv('OPENAI_API_KEY','fake-test-only-key')
    payload={'id':'mock','status':'completed','output':[{'content':[{'type':'output_text','text':'Customer deposits were $50 billion [S1].'}]}]}
    with patch('bankscope.generation.request_response',return_value=payload), patch('bankscope.api.generate',side_effect=lambda q,h:generate(q,h,str(tmp_path/'ledger.sqlite3'))):
        result=client.post('/query',json={'question':'Customer deposits','company':'Bank','year':2022,'generate_answer':True})
    assert result.status_code==200
    body=result.json()
    assert body['sources'][0]['page']==1
    assert body['generation']['warnings']
    assert body['generation']['sources']['S1']=='[BANK_2022, PDF page 1]'


def test_default_configuration_cannot_make_paid_calls(client):
    with patch('bankscope.generation.request_response') as provider:
        result=client.post('/query',json={'question':'Customer deposits','generate_answer':True})
    assert result.status_code==400
    assert 'disabled' in result.json()['detail']
    provider.assert_not_called()


def test_unexpected_internal_errors_do_not_echo_secrets(client):
    with patch('bankscope.api.generate',side_effect=RuntimeError('sk-private key and private request')):
        result=client.post('/query',json={'question':'Customer deposits','generate_answer':True})
    assert result.status_code==502
    assert 'sk-private' not in result.text


@pytest.mark.parametrize('strategy',['unknown','DENSE',"bm25; DROP TABLE documents"])
def test_invalid_strategy_is_rejected(client,strategy):
    assert client.post('/query',json={'question':'deposits','strategy':strategy}).status_code==422
