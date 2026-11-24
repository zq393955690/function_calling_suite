# Derived from langgenius/dify-official-plugins (agent), Apache-2.0.
# Modified for Function Calling Suite.

"""function_calling_off: no history is injected into the model.

The transcript is still recorded by the shared implementation, so switching to
a history strategy later can continue the conversation.
"""

from typing import ClassVar

# 以模块方式导入：直接 import 基类会让加载器的子类枚举看到两个候选。
from strategies import function_calling as _base


class FunctionCallingOffAgentStrategy(_base.FunctionCallingAgentStrategy):
    history_mode: ClassVar[str] = "off"
