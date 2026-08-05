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

"""Local connection package for the FAIM Cortex AGI Engine.

Re-exports the public API so that existing import paths like
``from ...connections.local_connection import LocalAgentConfig``
continue to work without changes.
"""

from core.cortex.cortexagi.connections.local.event_processor import LocalConnectionStep
from core.cortex.cortexagi.connections.local.litert_connection_config import LiteRTAgentConfig
from core.cortex.cortexagi.connections.local.litert_connection_config import LiteRTBackend
from core.cortex.cortexagi.connections.local.local_connection import callable_to_tool_proto
from core.cortex.cortexagi.connections.local.local_connection import LocalConnection
from core.cortex.cortexagi.connections.local.local_connection import LocalConnectionStrategy
from core.cortex.cortexagi.connections.local.local_connection_config import LocalAgentConfig
from core.cortex.cortexagi.connections.local.local_openai_connection_config import LocalOpenAIAgentConfig
from core.cortex.cortexagi.connections.local.types import EditFileResult
from core.cortex.cortexagi.connections.local.types import FindFileResult
from core.cortex.cortexagi.connections.local.types import GenerateImageResult
from core.cortex.cortexagi.connections.local.types import ListDirectoryEntry
from core.cortex.cortexagi.connections.local.types import ListDirectoryResult
from core.cortex.cortexagi.connections.local.types import RunCommandResult
from core.cortex.cortexagi.connections.local.types import SearchDirectoryResult
from core.cortex.cortexagi.connections.local.types import TextResult
from core.cortex.cortexagi.connections.local.types import ToolOutput
