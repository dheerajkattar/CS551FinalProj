import os
from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)

# Database configuration from environment variable
# Default to SQLite for local development, override for cloud deployment
db_url = os.getenv('DATABASE_URL', 'sqlite:///items.db')
app.config['SQLALCHEMY_DATABASE_URI'] = db_url
app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
    'pool_size': 10,
    'pool_recycle': 3600,
    'pool_pre_ping': True,
}

db = SQLAlchemy(app)

class Item(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.String(500))

    def to_dict(self):
        return {'id': self.id, 'name': self.name, 'description': self.description}

with app.app_context():
    db.create_all()

# CREATE
@app.route('/items', methods=['POST'])
def create_item():
    data = request.json
    item = Item(name=data.get('name'), description=data.get('description'))
    db.session.add(item)
    db.session.commit()
    return jsonify(item.to_dict()), 201

# READ all
@app.route('/items', methods=['GET'])
def get_items():
    items = Item.query.all()
    return jsonify([item.to_dict() for item in items]), 200

# READ one
@app.route('/items/<int:id>', methods=['GET'])
def get_item(id):
    item = Item.query.get(id)
    if not item:
        return jsonify({'error': 'Item not found'}), 404
    return jsonify(item.to_dict()), 200

# UPDATE
@app.route('/items/<int:id>', methods=['PUT'])
def update_item(id):
    item = Item.query.get(id)
    if not item:
        return jsonify({'error': 'Item not found'}), 404
    data = request.json
    item.name = data.get('name', item.name)
    item.description = data.get('description', item.description)
    db.session.commit()
    return jsonify(item.to_dict()), 200

# DELETE
@app.route('/items/<int:id>', methods=['DELETE'])
def delete_item(id):
    item = Item.query.get(id)
    if not item:
        return jsonify({'error': 'Item not found'}), 404
    db.session.delete(item)
    db.session.commit()
    return jsonify(item.to_dict()), 200

@app.route('/health', methods=['GET'])
def health():
    return jsonify({'status': 'healthy'}), 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', debug=True, port=5000)
