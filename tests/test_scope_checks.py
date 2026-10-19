import pytest
from bankscope.generation import generate
from bankscope.scope_checks import historical_scope_limit

HITS=[{'year':2022}]


@pytest.mark.parametrize('question',[
    'What were customer deposits in fiscal year 2035?',
    'What was net income in fiscal year 2040?',
    'What is the current real-time CET1 capital ratio?',
    'What is the private account balance of customer Jane Example?',
    'What is the password of customer Jane Example?',
    'What is the credit card PIN of customer Jane Example?',
])
def test_out_of_scope_abstains_without_key_or_paid_request(question,tmp_path):
    ledger=tmp_path/'calls.db'
    result=generate(question,HITS,ledger)
    assert result['status']=='abstained'
    assert result['paid_call_made'] is False
    assert not ledger.exists()


@pytest.mark.parametrize('question',[
    'What were customer deposits in fiscal year 2022?',
    'What were projected customer deposits in fiscal year 2025?',
    'What were scheduled maturities for fiscal year 2025?',
    'What are total private banking customer deposits?',
    'What was revenue in fiscal year 2023?',
    'What does the report say about real-time payment infrastructure?',
    'What is the bank policy to protect customer passwords?',
])
def test_in_scope_or_undetermined_questions_are_not_blanket_rejected(question):
    hits=[{'year':2023}]
    assert historical_scope_limit(question,hits) is None
