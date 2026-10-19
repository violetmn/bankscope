from bankscope.config import load_private_env


def test_private_env_preserves_exported_settings_and_literal_secrets(tmp_path,monkeypatch,capsys):
    p=tmp_path/'.env';p.write_text('OPENAI_API_KEY=fixture-${NOT_INTERPOLATED}\nBANKSCOPE_ENABLE_PAID=0\n')
    monkeypatch.delenv('OPENAI_API_KEY',raising=False)
    monkeypatch.setenv('BANKSCOPE_ENABLE_PAID','1')
    load_private_env(p)
    import os
    assert os.getenv('OPENAI_API_KEY')=='fixture-${NOT_INTERPOLATED}'
    assert os.getenv('BANKSCOPE_ENABLE_PAID')=='1'
    assert capsys.readouterr().out==''
    monkeypatch.delenv('OPENAI_API_KEY')
