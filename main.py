import os
import sys

def main():
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    # Add root dir to sys.path programmatically just in case
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    uvicorn.run("opscore.main:app", host="0.0.0.0", port=port, reload=False)

if __name__ == "__main__":
    main()
