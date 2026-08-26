from dotenv import load_dotenv
import os

print("CLIENT ID END:", repr(os.getenv("GOOGLE_CLIENT_ID", "")[-20:]))
print("SECRET LENGTH:", len(os.getenv("GOOGLE_CLIENT_SECRET", "")))
print("SECRET START:", repr(os.getenv("GOOGLE_CLIENT_SECRET", "")[:8]))

from app import create_app
load_dotenv()
app = create_app()

if __name__ == '__main__':
    app.run(debug=False)