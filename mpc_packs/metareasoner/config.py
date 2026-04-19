from dataclasses import dataclass, field
from typing import List

@dataclass
class MetareasonerConfig:
    dependencies: List[str] = field(default_factory=list)
