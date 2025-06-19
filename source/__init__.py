import argparse
from .server_dummy import mcp

def main():
    parser = argparse.ArgumentParser(
        description="Exposes Tachyon Search as MCP"
    )
    parser.parse_args()
    mcp.run()

if __name__ == "__main__":
    main()