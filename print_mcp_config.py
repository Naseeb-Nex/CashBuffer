import json

print("\n--- PI MCP CONFIGURATION ---")
print(
    "Add this to your local Pi agent configuration (~/.pi/config.json or equivalent) to let firstmate natively use your Neon DB:"
)
print(
    json.dumps(
        {
            "mcpServers": {
                "cashbuffer-db": {
                    "command": "/bin/bash",
                    "args": ["/Users/aiwithnex/Projects/firstmate/projects/CashBuffer/local-mcp-server.sh"],
                }
            }
        },
        indent=2,
    )
)
print("----------------------------\n")
