from mcp.server.fastmcp import FastMCP
from rag.tools import create_ticket, search_docs
  
mcp = FastMCP("nexus-hr-agent")

@mcp.tool()
def create_support_ticket(title: str, description: str) -> dict:
      """Create a support ticket with a title and description."""
      return create_ticket(title, description)

@mcp.tool()
def search_documentation(query: str) -> dict:
    """Search the documentation for a given query."""
    return search_docs(query)

if __name__ == "__main__":
    mcp.run()