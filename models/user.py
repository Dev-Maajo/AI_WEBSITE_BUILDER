from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from models.database import db
from functools import wraps

user_bp = Blueprint('user', __name__)

# Add this to models/user.py (at the top)

class User:
    def __init__(self, id, username, email, role):
        self.id = id
        self.username = username
        self.email = email
        self.role = role

    def to_dict(self):
        return {
            'id': self.id,
            'username': self.username,
            'email': self.email,
            'role': self.role
        }

    @staticmethod
    def find_by_id(user_id):
        cursor = db.cursor()
        result = cursor.execute("SELECT id, username, email, role FROM users WHERE id = ?", (user_id,))
        row = result.fetchone()
        return User(*row) if row else None

    @staticmethod
    def find_by_email(email):
        cursor = db.cursor()
        result = cursor.execute("SELECT id, username, email, role FROM users WHERE email = ?", (email,))
        row = result.fetchone()
        return User(*row) if row else None

    @staticmethod
    def find_all():
        cursor = db.cursor()
        result = cursor.execute("SELECT id, username, email, role FROM users")
        rows = result.fetchall()
        return [User(*row) for row in rows]

    def save(self):
        cursor = db.cursor()
        cursor.execute("UPDATE users SET username = ?, email = ?, role = ? WHERE id = ?", 
                       (self.username, self.email, self.role, self.id))
        db.commit()


def admin_required(f):
    """Decorator to require admin role"""
    @wraps(f)
    @jwt_required()
    def decorated_function(*args, **kwargs):
        current_user_id = get_jwt_identity()
        user = User.find_by_id(current_user_id)
        
        if not user or user.role != 'admin':
            return jsonify({'error': 'Admin access required'}), 403
        
        return f(*args, **kwargs)
    return decorated_function

@user_bp.route('/users', methods=['GET'])
@admin_required
def get_all_users():
    try:
        users = User.find_all()
        return jsonify({'users': [user.to_dict() for user in users]}), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@user_bp.route('/users/<user_id>', methods=['GET'])
@admin_required
def get_user(user_id):
    try:
        user = User.find_by_id(user_id)
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        return jsonify({'user': user.to_dict()}), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@user_bp.route('/users/<user_id>', methods=['PUT'])
@admin_required
def update_user(user_id):
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({'error': 'No data provided'}), 400
        
        user = User.find_by_id(user_id)
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        # Update user fields
        if 'username' in data:
            user.username = data['username']
        if 'email' in data:
            # Check if email already exists
            existing_user = User.find_by_email(data['email'])
            if existing_user and str(existing_user.id) != user_id:
                return jsonify({'error': 'Email already exists'}), 409
            user.email = data['email']
        if 'role' in data:
            valid_roles = ['admin', 'editor', 'viewer']
            if data['role'] not in valid_roles:
                return jsonify({'error': f'Invalid role. Must be one of: {", ".join(valid_roles)}'}), 400
            user.role = data['role']
        
        user.save()
        
        return jsonify({
            'message': 'User updated successfully',
            'user': user.to_dict()
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@user_bp.route('/users/<user_id>', methods=['DELETE'])
@admin_required
def delete_user(user_id):
    try:
        current_user_id = get_jwt_identity()
        
        # Don't allow admin to delete themselves
        if user_id == current_user_id:
            return jsonify({'error': 'Cannot delete your own account'}), 400
        
        user = User.find_by_id(user_id)
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        # Delete user and their websites
        cursor = db.cursor()
        cursor.execute('DELETE FROM websites WHERE user_id = ?', (user_id,))
        cursor.execute('DELETE FROM users WHERE id = ?', (user_id,))
        db.commit()
        
        return jsonify({'message': 'User deleted successfully'}), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

