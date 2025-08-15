from dataclasses import dataclass
from typing import Optional, Union, Literal

class AgentConfig:
    def __init__(self, config: Optional[dict] = {}):
        self.set_values_from_dict(config)

    def set(self, key: str, value: Union[str, int, float, bool]):
        """Set a configuration value."""
        setattr(self, key, value)

    def get(self, key: str, default: Optional[Union[str, int, float, bool]] = None) -> Optional[Union[str, int, float, bool]]:
        """Get a configuration value."""
        return getattr(self, key, default)
    def has(self, key: str) -> bool:
        """Check if a configuration value exists."""
        return hasattr(self, key)
    def set_values_from_dict(self, config: dict):
        """Set multiple configuration values from a dictionary."""
        for key, value in config.items():
            self.set(key, value)
    def to_dict(self) -> dict:
        """Convert the configuration to a dictionary."""
        return {key: getattr(self, key) for key in self.__dict__ if not key.startswith('_')}
    def __repr__(self):
        """String representation of the configuration."""
        return f"{self.__class__.__name__}({self.to_dict()})"
    def __str__(self):
        return f"{self.__class__.__name__}({self.to_dict()})"
    
    @staticmethod
    def from_dict(config: dict) -> 'AgentConfig':
        """Create an AgentConfig instance from a dictionary."""
        instance = AgentConfig(config)
        return instance
    @staticmethod
    def from_json(json_str: str) -> 'AgentConfig':
        """Create an AgentConfig instance from a JSON string."""
        import json
        config = json.loads(json_str)
        return AgentConfig.from_dict(config)
    
    @staticmethod
    def from_env(prefix: str = "AGENT_") -> 'AgentConfig':
        """Create an AgentConfig instance from environment variables."""
        import os
        config = {key[len(prefix):].lower(): os.getenv(key) for key in os.environ if key.startswith(prefix)}
        return AgentConfig.from_dict(config)
    @staticmethod
    def from_pre_set(pre_set_name: str) -> 'AgentConfig':
        """Set values from a pre-defined set of configurations."""
        pass
    @staticmethod
    def as_default() -> 'AgentConfig':
        """Return a default AgentConfig instance."""
        return AgentConfig({
            "name": "DefaultAgent",
            "description": "This is a default agent configuration.",
            "llm_provider": "openai",
            "llm_model": "gpt-5-mini",
            "user_db": "postgres",
            "checkpoint_type": "postgres",
            "rag_db": "chroma",
        })