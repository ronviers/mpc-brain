from dataclasses import dataclass, field
from typing import List

@dataclass
class SymbolicForebrainConfig:
    dependencies: List[str] = field(default_factory=list)
    declared_mutations: List[str] = field(default_factory=lambda: ['load', 'shed_load', 'local_budget', 'ops.reset'])
