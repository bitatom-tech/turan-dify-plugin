from dify_plugin import ToolProvider
from dify_plugin.errors.tool import ToolProviderCredentialValidationError

from turan.client import Client
from turan.core import Deadline, TuranError


class TuranProvider(ToolProvider):
    def _validate_credentials(self, credentials):
        key = credentials.get("api_key", "")
        if not isinstance(key, str) or not key.strip():
            raise ToolProviderCredentialValidationError("Enter your Turan API Key. / 请填写 Turan API Key。")
        client = Client(key, Deadline(25))
        try:
            client.authenticate()
        except TuranError as error:
            raise ToolProviderCredentialValidationError(error.public_message()) from None
        except Exception:
            raise ToolProviderCredentialValidationError("Unable to verify Turan credentials. Check the connection. / 无法验证图然凭证，请检查连接。") from None
        finally:
            client.close()
