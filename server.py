from flask import Flask, request, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

@app.route('/login', methods=['POST'])
def login():
    data = request.json
    if data:
        email = data.get('email')
        password = data.get('password')

        if not email or not password:
            return jsonify({"message": "Email and password are required"}), 400

        #just a dummy validation bro
        if email == "test@example.com" and password == "password123":
            print(f"Received login request with email: {email}")
            return jsonify({"message": "Login successful", "email": email})
        else:
            return jsonify({"message": "Invalid email or password"}), 401
    else:
        print("No data received")
        return jsonify({"message": "No data received"}), 400



if __name__ == "__main__":
    app.run(debug=True)
