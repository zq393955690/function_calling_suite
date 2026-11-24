# Derived from langgenius/dify-official-plugins (agent), Apache-2.0.
# Modified for Function Calling Suite.

import sys

sys.path.append("../..")

from dify_plugin import DifyPluginEnv, Plugin

plugin = Plugin(DifyPluginEnv(MAX_REQUEST_TIMEOUT=240, MAX_INVOCATION_TIMEOUT=900))

if __name__ == "__main__":
    plugin.run()
