import json
import pytest
from pydantic import ValidationError, SecretStr

from hive.config.schema import (
    MCPServerConfig,
    GatewayConfig,
    AgentDefaults,
    SlackConfig,
    WebSearchConfig
)
from hive.agent.tools.web import WebFetchTool, _validate_url


def test_py1_env_var_secrets():
    """Verify PY.1 / PY.2 Env Var SecretStr masking."""
    config = MCPServerConfig(
        command="npx",
        env={"API_KEY": "super_secret_value"}
    )
    
    # Assert it was cast to a SecretStr
    assert isinstance(config.env["API_KEY"], SecretStr)
    
    # Assert string representation is masked
    assert "super_secret_value" not in str(config.env["API_KEY"])
    assert str(config.env["API_KEY"]) == "**********"
    
    # Assert we can extract it when needed (mcp.py behavior)
    assert config.env["API_KEY"].get_secret_value() == "super_secret_value"


def test_py2_ssrf_validator():
    """Verify PY.2 web_fetch SSRF blocklist."""
    
    # Standard public domains should pass
    is_valid, err = _validate_url("https://www.google.com")
    assert is_valid is True
    
    # Missing scheme should fail
    is_valid, err = _validate_url("www.google.com")
    assert is_valid is False
    assert "Only http/https allowed" in err
    
    # Localhost IPv4 should fail
    is_valid, err = _validate_url("http://127.0.0.1")
    assert is_valid is False
    assert "private/internal hosts is not permitted" in err
    
    # Localhost IPv6 should fail
    is_valid, err = _validate_url("http://[::1]")
    assert is_valid is False
    assert "private/internal hosts is not permitted" in err
    
    # Private network (10.x.x.x) should fail
    is_valid, err = _validate_url("https://10.0.0.5/admin")
    assert is_valid is False
    assert "private/internal hosts is not permitted" in err
    
    # Cloud Metadata endpoint should fail
    is_valid, err = _validate_url("http://169.254.169.254/latest/meta-data/")
    assert is_valid is False
    assert "private/internal hosts is not permitted" in err

    # IPv4-mapped IPv6 localhost format shouldn't bypass
    is_valid, err = _validate_url("http://[0:0:0:0:0:ffff:127.0.0.1]/")
    assert is_valid is False
    assert "private/internal hosts is not permitted" in err

    # 0.0.0.0 (all interfaces bind) shouldn't bypass
    is_valid, err = _validate_url("http://0.0.0.0:8000")
    assert is_valid is False
    assert "private/internal hosts is not permitted" in err

    # 172.16 private range shouldn't bypass
    is_valid, err = _validate_url("http://172.20.5.1/api")
    assert is_valid is False
    assert "private/internal hosts is not permitted" in err

    # 192.168 private range shouldn't bypass
    is_valid, err = _validate_url("http://192.168.1.100")
    assert is_valid is False
    assert "private/internal hosts is not permitted" in err


@pytest.mark.asyncio
async def test_py2_ssrf_redirect_blocker(monkeypatch):
    """Verify PY.2 catches SSRF redirects using httpx mock."""
    tool = WebFetchTool()
    
    # We will patch httpx.AsyncClient.get to simulate a redirect to localhost
    class MockResponse:
        def __init__(self):
            self.url = "http://127.0.0.1/admin"
            self.headers = {"content-type": "text/html"}
            self.text = "admin panel"
            self.status_code = 200
            
        def raise_for_status(self):
            pass

    async def mock_get(*args, **kwargs):
        return MockResponse()
        
    import httpx
    monkeypatch.setattr(httpx.AsyncClient, "get", mock_get)
    
    # Fetching a "public" URL that resolves/redirects to localhost
    result_json = await tool.execute("http://public-redirect.com")
    result = json.loads(result_json)
    
    assert "error" in result
    assert result["error"] == "Redirect to private host blocked"


def test_py3_numeric_bounds():
    """Verify PY.3 numerical bounds prevent excessive / negative integer inputs."""
    
    # Valid Gateway port
    GatewayConfig(port=8080)
    
    # Invalid Gateway port (above 65535)
    with pytest.raises(ValidationError) as exc:
        GatewayConfig(port=99999)
    assert "Input should be less than or equal to 65535" in str(exc.value)

    # Invalid Gateway port (below 1)
    with pytest.raises(ValidationError) as exc:
        GatewayConfig(port=0)
    assert "Input should be greater than or equal to 1" in str(exc.value)
    
    # Valid Max Tokens
    AgentDefaults(max_tokens=1000)
    
    # Invalid Max Tokens (less than 1)
    with pytest.raises(ValidationError) as exc:
        AgentDefaults(max_tokens=0)
    assert "Input should be greater than or equal to 1" in str(exc.value)

    # Invalid Max Tokens (greater than 200k)
    with pytest.raises(ValidationError) as exc:
        AgentDefaults(max_tokens=250000)
    assert "Input should be less than or equal to 200000" in str(exc.value)

    # Email polling intervals shouldn't allow sub-5 second spamming
    from hive.config.schema import EmailConfig
    with pytest.raises(ValidationError) as exc:
        EmailConfig(poll_interval_seconds=1)
    assert "Input should be greater than or equal to 5" in str(exc.value)

    # Email config shouldn't allow millions of bytes to be ingested
    with pytest.raises(ValidationError) as exc:
        EmailConfig(max_body_chars=2000000)
    assert "Input should be less than or equal to 1000000" in str(exc.value)


def test_py4_literal_enum_types():
    """Verify PY.4 literal enums prevent typo config bypasses."""
    
    # Valid Slack Socket Mode
    SlackConfig(mode="socket")
    
    # Invalid Slack Socket Mode typo
    with pytest.raises(ValidationError) as exc:
        SlackConfig(mode="socekt") 
    assert "Input should be 'socket'" in str(exc.value)
    
    # Valid role
    SlackConfig(role="admin")
    
    # Invalid role
    with pytest.raises(ValidationError) as exc:
        SlackConfig(role="superadmin") 
    assert "Input should be 'user', 'admin' or 'notification'" in str(exc.value)


def test_py5_strict_extras():
    """Verify PY.5 extra='forbid' prevents silent dropping of unknown keys."""
    
    # Valid exact schema
    WebSearchConfig(api_key="valid")
    
    # Extra typo key (previously this would silently drop the key and load fine)
    with pytest.raises(ValidationError) as exc:
        WebSearchConfig(api_key="valid", maxTokenns=50)
        
    assert "Extra inputs are not permitted" in str(exc.value)
    assert "maxTokenns" in str(exc.value)

    # Nested typo keys should also be caught at the WebTools layer
    from hive.config.schema import WebToolsConfig
    with pytest.raises(ValidationError) as exc:
        WebToolsConfig(search={"api_key": "x", "unknown_key_inner": True})
    assert "Extra inputs are not permitted" in str(exc.value)

    # And even in completely un-related domains like Mochat configs
    from hive.config.schema import MochatConfig
    with pytest.raises(ValidationError) as exc:
        MochatConfig(refresh_intrval_ms=5000) # testing common typo
    assert "Extra inputs are not permitted" in str(exc.value)
    
    with pytest.raises(ValidationError) as exc:
        MochatConfig(reply_delay_mode="invalid_enum_value")
    assert "Input should be 'off' or 'non-mention'" in str(exc.value)
