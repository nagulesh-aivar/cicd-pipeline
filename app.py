# Sample application - Replace with your actual application code
from flask import Flask

app = Flask(__name__)

@app.route('/')
def hello():
    return 'Hello, World! Your CI/CD pipeline is working!'

@app.route('/health')
def health():
    return {'status': 'healthy'}, 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8000)

