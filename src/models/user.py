from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)
    card_balance = db.Column(db.Float, default=0.0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'<User {self.username}>'

    def to_dict(self):
        return {
            'id': self.id,
            'username': self.username,
            'email': self.email,
            'card_balance': self.card_balance,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }

class Transaction(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    transaction_type = db.Column(db.String(20), nullable=False)  # 'recharge' or 'usage'
    description = db.Column(db.String(255))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    user = db.relationship('User', backref=db.backref('transactions', lazy=True))

    def __repr__(self):
        return f'<Transaction {self.id}: {self.transaction_type} - {self.amount}>'

    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'amount': self.amount,
            'transaction_type': self.transaction_type,
            'description': self.description,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }

class BusRoute(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    route_number = db.Column(db.String(20), nullable=False)
    route_name = db.Column(db.String(100), nullable=False)
    origin = db.Column(db.String(100), nullable=False)
    destination = db.Column(db.String(100), nullable=False)
    fare = db.Column(db.Float, nullable=False)
    active = db.Column(db.Boolean, default=True)

    def __repr__(self):
        return f'<BusRoute {self.route_number}: {self.route_name}>'

    def to_dict(self):
        return {
            'id': self.id,
            'route_number': self.route_number,
            'route_name': self.route_name,
            'origin': self.origin,
            'destination': self.destination,
            'fare': self.fare,
            'active': self.active
        }

class BusLocation(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    route_id = db.Column(db.Integer, db.ForeignKey('bus_route.id'), nullable=False)
    bus_number = db.Column(db.String(20), nullable=False)
    latitude = db.Column(db.Float, nullable=False)
    longitude = db.Column(db.Float, nullable=False)
    last_updated = db.Column(db.DateTime, default=datetime.utcnow)
    
    route = db.relationship('BusRoute', backref=db.backref('bus_locations', lazy=True))

    def __repr__(self):
        return f'<BusLocation {self.bus_number}: {self.latitude}, {self.longitude}>'

    def to_dict(self):
        return {
            'id': self.id,
            'route_id': self.route_id,
            'bus_number': self.bus_number,
            'latitude': self.latitude,
            'longitude': self.longitude,
            'last_updated': self.last_updated.isoformat() if self.last_updated else None,
            'route': self.route.to_dict() if self.route else None
        }


class Rating(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    overall_rating = db.Column(db.Integer, nullable=False)
    punctuality_rating = db.Column(db.Integer, default=0)
    cleanliness_rating = db.Column(db.Integer, default=0)
    comfort_rating = db.Column(db.Integer, default=0)
    service_rating = db.Column(db.Integer, default=0)
    comments = db.Column(db.Text)
    bus_line = db.Column(db.String(100))
    trip_date = db.Column(db.Date)
    trip_time = db.Column(db.Time)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    user = db.relationship('User', backref=db.backref('ratings', lazy=True))

    def __repr__(self):
        return f'<Rating {self.id}: {self.overall_rating} stars by user {self.user_id}>'

    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'overall_rating': self.overall_rating,
            'punctuality_rating': self.punctuality_rating,
            'cleanliness_rating': self.cleanliness_rating,
            'comfort_rating': self.comfort_rating,
            'service_rating': self.service_rating,
            'comments': self.comments,
            'bus_line': self.bus_line,
            'trip_date': self.trip_date.isoformat() if self.trip_date else None,
            'trip_time': self.trip_time.isoformat() if self.trip_time else None,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }

