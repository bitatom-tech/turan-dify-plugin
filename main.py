from dify_plugin import DifyPluginEnv, Plugin
from turan.limits import TRANSPORT_TIMEOUT_SECONDS

# Transport connection lifetime must exceed the eight-minute business budget.
# Host daemon and workflow limits remain deployment requirements.
plugin = Plugin(DifyPluginEnv(MAX_REQUEST_TIMEOUT=TRANSPORT_TIMEOUT_SECONDS))

if __name__ == "__main__":
    plugin.run()
