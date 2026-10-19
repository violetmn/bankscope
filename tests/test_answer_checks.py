from decimal import Decimal
import pytest
from bankscope.answer_checks import amounts, citation_ids, numeric_warnings, reconcile_components


@pytest.mark.parametrize('text,expected',[
    ('Assets [S1].', {'1'}),
    ('Assets [S1, S2] and [S2].', {'1','2'}),
    ('Assets [S1] [S999].', {'1','999'}),
    ('See [S1, S999].', {'1','999'}),
    ('No citations here.', set()),
])
def test_citation_groups(text,expected):
    assert citation_ids(text)==expected


@pytest.mark.parametrize('text,value',[
    ('$110.239 billion', Decimal('110239000000')),
    ('$110,239 million', Decimal('110239000000')),
    ('EUR 15 million', Decimal('15000000')),
    ('£-2.5 million', Decimal('-2500000')),
])
def test_amount_unit_normalization(text,value):
    assert list(amounts(text))[0][2]==value


def test_equivalent_billion_and_million_magnitudes_are_supported():
    hits=[{'text':'Customer deposits (Millions) 2022 2021 Total $110,239 $84,382'}]
    assert numeric_warnings('Customer deposits were $110.239 billion [S1].',hits)==[]


def test_factor_of_thousand_error_is_flagged():
    hits=[{'text':'Total deposits $110,239 million.'}]
    assert numeric_warnings('Deposits were $110.239 million [S1].',hits)


def test_wrong_currency_is_flagged_in_explicit_amounts():
    assert numeric_warnings('Deposits were EUR 50 million [S1].',[{'text':'Deposits were USD 50 million.'}])


def test_uncited_evidence_cannot_support_a_number():
    cited=[{'text':'Total deposits $10 million.'}]
    assert numeric_warnings('Deposits were $20 million [S1].',cited)


def test_same_number_does_not_verify_year_or_label_documented_limit():
    # Do not mistake passing the magnitude check for full semantic verification.
    assert numeric_warnings('2023 revenue was $50 million [S1].',[{'text':'2022 deposits were $50 million.'}])==[]


def test_user_reported_incomplete_breakdown_regression():
    # Transcript values converted into explicit same-unit structured inputs.
    result=reconcile_components('110.239',['76.731','16.096','0.071','1.044'])
    assert result['matches'] is False
    assert Decimal(result['subtotal'])==Decimal('93.942')
    assert Decimal(result['difference'])==Decimal('16.297')


def test_complete_deposit_categories_reconcile_without_float_rounding():
    assert reconcile_components('110.239',['109.119','0.015','0.663','0.442'])['matches']
    assert reconcile_components('0.3',['0.1','0.2'])['matches']


@pytest.mark.parametrize('value',['NaN','Infinity','-Infinity'])
def test_non_finite_financial_inputs_rejected(value):
    with pytest.raises(ValueError):
        reconcile_components(value,['1'])
