# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Hooks package for the FAIM Cortex AGI Engine."""

from core.cortex.cortexagi.hooks import policy
from core.cortex.cortexagi.hooks.hooks import DecideHook
from core.cortex.cortexagi.hooks.hooks import HookContext
from core.cortex.cortexagi.hooks.hooks import InspectHook
from core.cortex.cortexagi.hooks.hooks import on_compaction
from core.cortex.cortexagi.hooks.hooks import on_interaction
from core.cortex.cortexagi.hooks.hooks import on_session_end
from core.cortex.cortexagi.hooks.hooks import on_session_start
from core.cortex.cortexagi.hooks.hooks import on_tool_error
from core.cortex.cortexagi.hooks.hooks import OnCompactionHook
from core.cortex.cortexagi.hooks.hooks import OnInteractionHook
from core.cortex.cortexagi.hooks.hooks import OnSessionEndHook
from core.cortex.cortexagi.hooks.hooks import OnSessionStartHook
from core.cortex.cortexagi.hooks.hooks import OnToolErrorHook
from core.cortex.cortexagi.hooks.hooks import post_tool_call
from core.cortex.cortexagi.hooks.hooks import post_turn
from core.cortex.cortexagi.hooks.hooks import PostToolCallHook
from core.cortex.cortexagi.hooks.hooks import PostTurnHook
from core.cortex.cortexagi.hooks.hooks import pre_tool_call_decide
from core.cortex.cortexagi.hooks.hooks import pre_turn
from core.cortex.cortexagi.hooks.hooks import PreToolCallDecideHook
from core.cortex.cortexagi.hooks.hooks import PreTurnHook
from core.cortex.cortexagi.hooks.hooks import TransformHook


__all__ = [
    "policy",
    "HookContext",
    "DecideHook",
    "InspectHook",
    "TransformHook",
    "OnCompactionHook",
    "OnInteractionHook",
    "OnSessionEndHook",
    "OnSessionStartHook",
    "OnToolErrorHook",
    "PostToolCallHook",
    "PostTurnHook",
    "PreToolCallDecideHook",
    "PreTurnHook",
    "on_compaction",
    "on_interaction",
    "on_session_end",
    "on_session_start",
    "on_tool_error",
    "post_tool_call",
    "post_turn",
    "pre_tool_call_decide",
    "pre_turn",
]
