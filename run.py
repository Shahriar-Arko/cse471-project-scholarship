from dotenv import load_dotenv
import os

load_dotenv()

print("CLIENT ID END:", repr(os.getenv("GOOGLE_CLIENT_ID", "")[-20:]))
print("SECRET LENGTH:", len(os.getenv("GOOGLE_CLIENT_SECRET", "")))
print("SECRET START:", repr(os.getenv("GOOGLE_CLIENT_SECRET", "")[:8]))

from app import create_app
app = create_app()
if __name__ == '__main__':
    app.run(debug=True, port=5000, use_reloader=False)