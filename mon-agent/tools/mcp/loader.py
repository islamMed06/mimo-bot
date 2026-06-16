import logging
log = logging.getLogger("MCP_LOADER")

class MCPLoader:
    def __init__(self, config):
        self.config = config

    def charger(self):
        outils = {}
        config_mcp = self.config.get("tools", {}).get("mcp", {})
        for nom, cfg in config_mcp.items():
            if isinstance(cfg, dict) and cfg.get("active", False):
                log.info(f"MCP outil detecte (non charge): {nom}")
            elif isinstance(cfg, bool) and cfg:
                log.info(f"MCP outil detecte (non charge): {nom}")
        return outils
