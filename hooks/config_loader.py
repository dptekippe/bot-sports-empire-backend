"""
Memory Contract Configuration Loader
Loads config.yaml and supports environment variable overrides
"""

import os
import yaml
from pathlib import Path
from typing import Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)


class ConfigLoader:
    """Load and manage Memory Contract configuration"""
    
    def __init__(self, config_path: Optional[str] = None):
        self.config_path = config_path or self._find_config_path()
        self.config = self._load_config()
        self._resolve_paths()
        self._ensure_directories()
        
    def _find_config_path(self) -> str:
        """Find config.yaml in standard locations"""
        # Check current directory
        current_dir = Path(__file__).parent
        config_path = current_dir / "config.yaml"
        if config_path.exists():
            return str(config_path)
        
        # Check workspace root
        workspace = os.environ.get("MEMORY_CONTRACT_WORKSPACE")
        if workspace:
            config_path = Path(workspace) / "hooks" / "config.yaml"
            if config_path.exists():
                return str(config_path)
        
        # Default location
        return str(current_dir / "config.yaml")
    
    def _load_config(self) -> Dict[str, Any]:
        """Load YAML config with environment variable support"""
        try:
            # TODO: Agent should read config file using OpenClaw read tool
            # with open(self.config_path, 'r') as f:
            #     raw_config = f.read()
            
            # For now, use default config
            print(f"[TODO] Would load config from {self.config_path}")
            return self._get_default_config()
            
            # Replace environment variable placeholders
            # config_text = self._replace_env_vars(raw_config)
            # config = yaml.safe_load(config_text)
            # 
            # # Apply environment variable overrides
            # config = self._apply_env_overrides(config)
            # 
            # logger.info(f"Loaded config from {self.config_path}")
            # return config
            
        except FileNotFoundError:
            logger.warning(f"Config file not found at {self.config_path}, using defaults")
            return self._get_default_config()
        except yaml.YAMLError as e:
            logger.error(f"Error parsing config file: {e}")
            raise
        except Exception as e:
            logger.error(f"Error loading config: {e}")
            raise
    
    def _replace_env_vars(self, text: str) -> str:
        """Replace ${VAR} with environment variable values"""
        import re
        
        def replace_match(match):
            var_name = match.group(1)
            return os.environ.get(var_name, match.group(0))
        
        # Replace ${VAR} patterns
        pattern = r'\$\{([A-Za-z0-9_]+)\}'
        return re.sub(pattern, replace_match, text)
    
    def _apply_env_overrides(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Apply environment variable overrides to config"""
        for key, value in config.items():
            if isinstance(value, dict):
                config[key] = self._apply_env_overrides(value)
            else:
                env_var = f"MEMORY_CONTRACT_{key.upper()}"
                if env_var in os.environ:
                    env_value = os.environ[env_var]
                    # Try to parse as appropriate type
                    if isinstance(value, bool):
                        config[key] = env_value.lower() in ('true', '1', 'yes')
                    elif isinstance(value, int):
                        try:
                            config[key] = int(env_value)
                        except ValueError:
                            config[key] = value
                    elif isinstance(value, float):
                        try:
                            config[key] = float(env_value)
                        except ValueError:
                            config[key] = value
                    else:
                        config[key] = env_value
        
        return config
    
    def _resolve_paths(self):
        """Resolve all path placeholders in config"""
        # First pass: resolve workspace
        workspace = self.config.get('workspace', '')
        if '${workspace}' in workspace:
            # This shouldn't happen after env var replacement, but just in case
            workspace = workspace.replace('${workspace}', '')
        
        # Second pass: resolve all paths
        def resolve_path(value, current_path=""):
            if isinstance(value, str):
                if '${workspace}' in value:
                    value = value.replace('${workspace}', workspace)
                if '${' in value:
                    value = self._replace_env_vars(value)
                # Convert to absolute path if it's a file/directory path
                if '/' in value or '\\' in value:
                    return os.path.expanduser(value)
                return value
            elif isinstance(value, dict):
                return {k: resolve_path(v, f"{current_path}.{k}" if current_path else k) 
                       for k, v in value.items()}
            elif isinstance(value, list):
                return [resolve_path(item, current_path) for item in value]
            else:
                return value
        
        self.config = resolve_path(self.config)
    
    def _ensure_directories(self):
        """Ensure all required directories exist"""
        directories = [
            self.config.get('workspace'),
            self.config.get('memory_dir'),
            self.config.get('hooks_dir'),
            self.config.get('logs_dir'),
        ]
        
        for directory in directories:
            if directory and not os.path.exists(directory):
                try:
                    os.makedirs(directory, exist_ok=True)
                    logger.info(f"Created directory: {directory}")
                except Exception as e:
                    logger.error(f"Failed to create directory {directory}: {e}")
                    raise
    
    def _get_default_config(self) -> Dict[str, Any]:
        """Get default configuration"""
        # Use current user's home directory as base
        home = os.path.expanduser("~")
        workspace = os.path.join(home, ".openclaw", "workspace")
        
        return {
            'workspace': workspace,
            'memory_dir': os.path.join(workspace, 'memory'),
            'hooks_dir': os.path.join(workspace, 'hooks'),
            'logs_dir': os.path.join(workspace, 'hooks', 'logs'),
            'compliance_file': os.path.join(workspace, 'memory_contract_compliance.json'),
            'decisions_file': os.path.join(workspace, 'DECISIONS.md'),
            'kill_switch_file': os.path.join(workspace, 'DISABLE_MEMORY_CONTRACT'),
            'search_log': os.path.join(workspace, 'hooks', 'logs', 'search_log.jsonl'),
            'write_log': os.path.join(workspace, 'hooks', 'logs', 'write_log.jsonl'),
            'validation_log': os.path.join(workspace, 'hooks', 'logs', 'validation_log.jsonl'),
            'error_log': os.path.join(workspace, 'hooks', 'logs', 'errors.jsonl'),
            'alert_log': os.path.join(workspace, 'hooks', 'logs', 'alerts.jsonl'),
            'performance_targets': {
                'search_latency_max': 500,
                'write_latency_max': 200,
                'validation_latency_max': 1000
            },
            'validation': {
                'memory_file_min_lines': 10,
                'recent_commit_hours': 6,
                'min_daily_searches': 1,
                'min_daily_writes': 1
            },
            'log_rotation': {
                'keep_days': 30,
                'compress_after_days': 7,
                'max_log_size_mb': 10
            },
            'features': {
                'enable_pre_action_search': True,
                'enable_post_decision_write': True,
                'enable_validation': True,
                'enable_compliance_tracking': True,
                'enable_log_rotation': True
            },
            'kill_switch': {
                'enabled': True,
                'check_environment': True,
                'check_file': True,
                'environment_var': 'MEMORY_CONTRACT_ENABLED'
            }
        }
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get configuration value using dot notation"""
        keys = key.split('.')
        value = self.config
        
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default
        
        return value
    
    def set(self, key: str, value: Any):
        """Set configuration value using dot notation"""
        keys = key.split('.')
        config = self.config
        
        for k in keys[:-1]:
            if k not in config:
                config[k] = {}
            config = config[k]
        
        config[keys[-1]] = value
    
    def save(self, path: Optional[str] = None):
        """Save configuration to file"""
        save_path = path or self.config_path
        try:
            # TODO: Agent should write config file using OpenClaw write tool
            # with open(save_path, 'w') as f:
            #     yaml.dump(self.config, f, default_flow_style=False)
            # logger.info(f"Saved config to {save_path}")
            print(f"[TODO] Would save config to {save_path}")
        except Exception as e:
            logger.error(f"Failed to save config: {e}")
            raise
    
    def validate(self) -> bool:
        """Validate configuration"""
        errors = []
        
        # Check required directories
        required_dirs = ['workspace', 'memory_dir', 'hooks_dir', 'logs_dir']
        for dir_key in required_dirs:
            path = self.get(dir_key)
            if not path:
                errors.append(f"Missing required directory: {dir_key}")
            elif not os.path.exists(path):
                try:
                    os.makedirs(path, exist_ok=True)
                except Exception as e:
                    errors.append(f"Cannot create directory {path}: {e}")
        
        # Check performance targets
        targets = self.get('performance_targets', {})
        if not isinstance(targets, dict):
            errors.append("performance_targets must be a dictionary")
        else:
            for target in ['search_latency_max', 'write_latency_max', 'validation_latency_max']:
                if target not in targets:
                    errors.append(f"Missing performance target: {target}")
                elif not isinstance(targets[target], (int, float)):
                    errors.append(f"Performance target {target} must be a number")
        
        if errors:
            logger.error(f"Configuration validation failed: {errors}")
            return False
        
        logger.info("Configuration validation passed")
        return True


# Global config instance
_config_instance = None

def get_config() -> ConfigLoader:
    """Get global configuration instance"""
    global _config_instance
    if _config_instance is None:
        _config_instance = ConfigLoader()
    return _config_instance


if __name__ == "__main__":
    # Test the config loader
    config = get_config()
    print("Configuration loaded successfully")
    print(f"Workspace: {config.get('workspace')}")
    print(f"Memory directory: {config.get('memory_dir')}")
    print(f"Validation: {config.validate()}")