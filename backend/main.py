from flask import Flask, request, jsonify
from algorithms.markov_chains import run_algorithm
from flask_cors import CORS
from utils.imports import *
from utils.logger import logger


app = Flask(__name__)
CORS(app)


@app.route("/run", methods=["POST"])
def run():
    logger.debug("Debug: Starting main script")
    if "csvFile" not in request.files:
        return "No file uploaded", 400

    file = request.files["dataFile"]
    csv_file_name = os.path.join(UPLOAD_FOLDER, file.filename)
    file.save(csv_file_name)
    data = request.json
    result = run_algorithm(data, csv_file_name)
    return jsonify(result)


if __name__ == "__main__":
    app.run(debug=True)
