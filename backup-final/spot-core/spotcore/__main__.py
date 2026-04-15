import os
import uvicorn
from .app import app

def main():
    host = os.getenv("SPOT_HOST", "0.0.0.0")
    port = int(os.getenv("SPOT_PORT", "8787"))
    uvicorn.run(app, host=host, port=port)

if __name__ == "__main__":
    main()
