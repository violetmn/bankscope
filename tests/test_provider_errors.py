import json
import ssl
import urllib.error
from io import BytesIO
from unittest.mock import patch
import pytest
from bankscope.generation import provider_error, request_response, GenerationError


@pytest.mark.parametrize('status,code,category',[
    (401,'invalid_api_key','authentication'),
    (403,None,'permission_or_access'),
    (429,'insufficient_quota','billing_or_quota'),
    (429,'rate_limit_exceeded','rate_or_usage_limit'),
    (404,'model_not_found','model_access'),
    (500,None,'provider_service'),
    (400,None,'provider_request'),
])
def test_error_categories_never_echo_provider_secrets(status,code,category):
    body=json.dumps({'error':{'code':code,'message':'sk-secret-value personal details'}})
    error=provider_error(status,body)
    assert error.category==category
    assert 'sk-secret-value' not in str(error)
    assert 'personal details' not in str(error)


def test_provider_error_body_is_sanitized():
    failure=urllib.error.HTTPError('https://api.openai.com/v1/responses',401,'Denied',{},BytesIO(b'{"error":{"message":"sk-private"}}'))
    with patch('urllib.request.urlopen',side_effect=failure):
        with pytest.raises(GenerationError,match='did not accept') as error:
            request_response(object())
    assert error.value.status==401
    assert 'sk-private' not in str(error.value)


def test_certificate_failure_identified_without_disabling_tls():
    with patch('urllib.request.urlopen',side_effect=urllib.error.URLError(ssl.SSLCertVerificationError('bad chain'))) as call:
        with pytest.raises(GenerationError) as error:
            request_response(object())
    assert error.value.category=='tls_certificate'
    assert call.call_args.kwargs['context'].verify_mode==ssl.CERT_REQUIRED


def test_network_failure_does_not_claim_a_billing_problem():
    with patch('urllib.request.urlopen',side_effect=urllib.error.URLError('network unavailable')):
        with pytest.raises(GenerationError) as error:
            request_response(object())
    assert error.value.category=='network_connection'


@pytest.mark.parametrize('body',[b'not-json',b'[]',b'{"error":null}',b'{"error":{"code":[]}}'])
def test_malformed_error_bodies_still_produce_safe_diagnostics(body):
    error=provider_error(400,body)
    assert error.category=='provider_request'


@pytest.mark.parametrize('failure',[
    TimeoutError('private timeout details'),
    urllib.error.URLError(TimeoutError('private timeout details')),
])
def test_both_timeout_forms_are_classified_without_echoing_details(failure):
    with patch('urllib.request.urlopen',side_effect=failure):
        with pytest.raises(GenerationError) as error:
            request_response(object())
    assert error.value.category=='network_timeout'
    assert 'private timeout details' not in str(error.value)
