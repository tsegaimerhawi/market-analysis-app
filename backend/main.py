from flask import Flask, request, jsonify
from algorithms.markov_chains import run_algorithm
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

@app.route('/run', methods=['POST'])
def run():
    data = request.json
    result = run_algorithm(data)
    return jsonify(result)

if __name__ == '__main__':
    app.run(debug=True)
