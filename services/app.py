from flask import Flask
from JD_services import jd_blueprint  # import your blueprint

def create_app():
    app = Flask(__name__)
    app.register_blueprint(jd_blueprint, url_prefix="/jd")  # register blueprint
    return app

if __name__ == "__main__":
    app = create_app()
    app.run(host="0.0.0.0", port=5001, debug=True)

