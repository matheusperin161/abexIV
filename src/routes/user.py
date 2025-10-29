from flask import Blueprint, jsonify, request, session
from werkzeug.security import generate_password_hash, check_password_hash
from src.models.user import User, Transaction, BusRoute, BusLocation, Rating, db
from datetime import datetime

user_bp = Blueprint('user', __name__)

# Rotas de autenticação
@user_bp.route('/register', methods=['POST'])
def register():
    data = request.json
    
    # Verificar se usuário já existe
    if User.query.filter_by(username=data['username']).first():
        return jsonify({'error': 'Usuário já existe'}), 400
    
    if User.query.filter_by(email=data['email']).first():
        return jsonify({'error': 'Email já cadastrado'}), 400
    
    # Criar novo usuário
    hashed_password = generate_password_hash(data['password'])
    user = User(
        username=data['username'], 
        email=data['email'],
        password=hashed_password,
        card_balance=0.0
    )
    
    db.session.add(user)
    db.session.commit()
    
    return jsonify({
        'message': 'Usuário criado com sucesso',
        'user': user.to_dict()
    }), 201

@user_bp.route('/login', methods=['POST'])
def login():
    data = request.json
    user = User.query.filter_by(username=data['username']).first()
    
    if user and check_password_hash(user.password, data['password']):
        session['user_id'] = user.id
        return jsonify({
            'message': 'Login realizado com sucesso',
            'user': user.to_dict()
        }), 200
    
    return jsonify({'error': 'Credenciais inválidas'}), 401

@user_bp.route('/logout', methods=['POST'])
def logout():
    session.pop('user_id', None)
    return jsonify({'message': 'Logout realizado com sucesso'}), 200

@user_bp.route('/profile', methods=['GET'])
def get_profile():
    if 'user_id' not in session:
        return jsonify({'error': 'Usuário não autenticado'}), 401
    
    user = User.query.get(session['user_id'])
    if not user:
        return jsonify({'error': 'Usuário não encontrado'}), 404
    
    return jsonify(user.to_dict())

@user_bp.route('/profile', methods=['PUT'])
def update_profile():
    if 'user_id' not in session:
        return jsonify({'error': 'Usuário não autenticado'}), 401
    
    user = User.query.get(session['user_id'])
    if not user:
        return jsonify({'error': 'Usuário não encontrado'}), 404
    
    data = request.json
    
    # Validar dados obrigatórios
    if not data.get('username') or not data.get('email'):
        return jsonify({'error': 'Nome de usuário e e-mail são obrigatórios'}), 400
    
    # Verificar se o novo username já existe (exceto para o usuário atual)
    existing_user = User.query.filter_by(username=data['username']).first()
    if existing_user and existing_user.id != user.id:
        return jsonify({'error': 'Nome de usuário já existe'}), 400
    
    # Verificar se o novo email já existe (exceto para o usuário atual)
    existing_email = User.query.filter_by(email=data['email']).first()
    if existing_email and existing_email.id != user.id:
        return jsonify({'error': 'E-mail já cadastrado'}), 400
    
    # Atualizar dados
    user.username = data['username']
    user.email = data['email']
    
    # Atualizar senha se fornecida
    if data.get('password'):
        user.password = generate_password_hash(data['password'])
    
    try:
        db.session.commit()
        return jsonify({
            'message': 'Perfil atualizado com sucesso',
            'username': user.username,
            'email': user.email
        }), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': 'Erro ao atualizar perfil'}), 500

# Rotas de saldo e transações
@user_bp.route('/balance', methods=['GET'])
def get_balance():
    if 'user_id' not in session:
        return jsonify({'error': 'Usuário não autenticado'}), 401
    
    user = User.query.get(session['user_id'])
    if not user:
        return jsonify({'error': 'Usuário não encontrado'}), 404
    
    return jsonify({'balance': user.card_balance})

@user_bp.route('/recharge', methods=['POST'])
def recharge_card():
    if 'user_id' not in session:
        return jsonify({'error': 'Usuário não autenticado'}), 401
    
    data = request.json
    amount = float(data.get('amount', 0))
    payment_method = data.get('payment_method', 'cartao')
    
    if amount <= 0:
        return jsonify({'error': 'Valor deve ser maior que zero'}), 400
    
    # Validar método de pagamento
    valid_methods = ['cartao', 'pix', 'boleto']
    if payment_method not in valid_methods:
        return jsonify({'error': 'Método de pagamento inválido'}), 400
    
    user = User.query.get(session['user_id'])
    if not user:
        return jsonify({'error': 'Usuário não encontrado'}), 404
    
    # Simular processamento do pagamento baseado no método
    payment_status = 'pending'
    payment_info = {}
    
    if payment_method == 'cartao':
        # Simular processamento de cartão (instantâneo)
        payment_status = 'completed'
        payment_info = {
            'method': 'Cartão de Crédito',
            'status': 'Aprovado',
            'transaction_id': f'CARD_{user.id}_{int(datetime.now().timestamp())}'
        }
    elif payment_method == 'pix':
        # Simular PIX (instantâneo após confirmação)
        payment_status = 'completed'
        payment_info = {
            'method': 'PIX',
            'status': 'Aprovado',
            'transaction_id': f'PIX_{user.id}_{int(datetime.now().timestamp())}',
            'qr_code': 'data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChwGA60e6kgAAAABJRU5ErkJggg=='
        }
    elif payment_method == 'boleto':
        # Simular boleto (pendente até pagamento)
        payment_status = 'completed'  # Para fins de demonstração, vamos considerar como pago
        payment_info = {
            'method': 'Boleto Bancário',
            'status': 'Aprovado',
            'transaction_id': f'BOL_{user.id}_{int(datetime.now().timestamp())}',
            'barcode': '23793.39001 60000.000001 00000.000000 1 84770000010000'
        }
    
    # Atualizar saldo apenas se o pagamento foi aprovado
    if payment_status == 'completed':
        user.card_balance += amount
        
        # Registrar transação
        transaction = Transaction(
            user_id=user.id,
            amount=amount,
            transaction_type='recharge',
            description=f'Recarga via {payment_info["method"]} - R$ {amount:.2f}'
        )
        
        db.session.add(transaction)
        db.session.commit()
        
        return jsonify({
            'message': 'Recarga realizada com sucesso',
            'new_balance': user.card_balance,
            'transaction': transaction.to_dict(),
            'payment_info': payment_info
        }), 200
    else:
        return jsonify({
            'message': 'Pagamento pendente',
            'payment_info': payment_info
        }), 202

@user_bp.route('/transactions', methods=['GET'])
def get_transactions():
    if 'user_id' not in session:
        return jsonify({'error': 'Usuário não autenticado'}), 401
    
    transactions = Transaction.query.filter_by(user_id=session['user_id']).order_by(Transaction.created_at.desc()).all()
    return jsonify([transaction.to_dict() for transaction in transactions])

# Rotas de ônibus e rotas
@user_bp.route('/routes', methods=['GET'])
def get_bus_routes():
    routes = BusRoute.query.filter_by(active=True).all()
    return jsonify([route.to_dict() for route in routes])

@user_bp.route('/bus-locations/<int:route_id>', methods=['GET'])
def get_bus_locations(route_id):
    locations = BusLocation.query.filter_by(route_id=route_id).all()
    return jsonify([location.to_dict() for location in locations])

@user_bp.route('/use-transport', methods=['POST'])
def use_transport():
    if 'user_id' not in session:
        return jsonify({'error': 'Usuário não autenticado'}), 401
    
    data = request.json
    route_id = data.get('route_id')
    
    user = User.query.get(session['user_id'])
    route = BusRoute.query.get(route_id)
    
    if not user or not route:
        return jsonify({'error': 'Usuário ou rota não encontrada'}), 404
    
    if user.card_balance < route.fare:
        return jsonify({'error': 'Saldo insuficiente'}), 400
    
    # Debitar saldo
    user.card_balance -= route.fare
    
    # Registrar transação
    transaction = Transaction(
        user_id=user.id,
        amount=-route.fare,
        transaction_type='usage',
        description=f'Uso do transporte - Linha {route.route_number}'
    )
    
    db.session.add(transaction)
    db.session.commit()
    
    return jsonify({
        'message': 'Transporte utilizado com sucesso',
        'new_balance': user.card_balance,
        'transaction': transaction.to_dict()
    }), 200

# Rotas administrativas (para popular dados de exemplo)
@user_bp.route('/admin/populate-routes', methods=['POST'])
def populate_routes():
    # Verificar se já existem rotas
    if BusRoute.query.count() > 0:
        return jsonify({'message': 'Rotas já existem no banco de dados'}), 200
    
    # Criar rotas de exemplo
    routes = [
        BusRoute(route_number='001', route_name='Centro - Zona Norte', origin='Centro', destination='Zona Norte', fare=4.50),
        BusRoute(route_number='002', route_name='Centro - Zona Sul', origin='Centro', destination='Zona Sul', fare=4.50),
        BusRoute(route_number='003', route_name='Zona Leste - Centro', origin='Zona Leste', destination='Centro', fare=4.50),
        BusRoute(route_number='004', route_name='Zona Oeste - Centro', origin='Zona Oeste', destination='Centro', fare=4.50),
        BusRoute(route_number='005', route_name='Circular Shopping', origin='Terminal Central', destination='Shopping Center', fare=3.50),
    ]
    
    for route in routes:
        db.session.add(route)
    
    # Criar localizações de exemplo para os ônibus
    locations = [
        BusLocation(route_id=1, bus_number='1001', latitude=-23.5505, longitude=-46.6333),
        BusLocation(route_id=1, bus_number='1002', latitude=-23.5515, longitude=-46.6343),
        BusLocation(route_id=2, bus_number='2001', latitude=-23.5525, longitude=-46.6353),
        BusLocation(route_id=2, bus_number='2002', latitude=-23.5535, longitude=-46.6363),
        BusLocation(route_id=3, bus_number='3001', latitude=-23.5545, longitude=-46.6373),
    ]
    
    for location in locations:
        db.session.add(location)
    
    db.session.commit()
    
    return jsonify({'message': 'Rotas e localizações criadas com sucesso'}), 201


# Rotas de recuperação de senha
@user_bp.route('/forgot-password', methods=['POST'])
def forgot_password():
    data = request.json
    email = data.get('email')
    
    if not email:
        return jsonify({'error': 'Email é obrigatório'}), 400
    
    user = User.query.filter_by(email=email).first()
    if not user:
        # Por segurança, não revelamos se o email existe ou não
        return jsonify({'message': 'Se o email estiver cadastrado, você receberá instruções para redefinir sua senha'}), 200
    
    # Gerar token de recuperação (simulado - em produção usaria um token seguro)
    import secrets
    reset_token = secrets.token_urlsafe(32)
    
    # Em uma aplicação real, você salvaria o token no banco com expiração
    # e enviaria por email. Aqui vamos simular retornando o token
    
    # Simular envio de email (em produção, usar serviço de email real)
    return jsonify({
        'message': 'Se o email estiver cadastrado, você receberá instruções para redefinir sua senha',
        'reset_token': reset_token,  # Apenas para demonstração - remover em produção
        'user_id': user.id  # Apenas para demonstração - remover em produção
    }), 200

@user_bp.route('/reset-password', methods=['POST'])
def reset_password():
    data = request.json
    user_id = data.get('user_id')  # Em produção, isso viria do token
    new_password = data.get('new_password')
    confirm_password = data.get('confirm_password')
    
    if not user_id or not new_password or not confirm_password:
        return jsonify({'error': 'Todos os campos são obrigatórios'}), 400
    
    if new_password != confirm_password:
        return jsonify({'error': 'As senhas não coincidem'}), 400
    
    if len(new_password) < 6:
        return jsonify({'error': 'A senha deve ter pelo menos 6 caracteres'}), 400
    
    user = User.query.get(user_id)
    if not user:
        return jsonify({'error': 'Usuário não encontrado'}), 404
    
    # Atualizar senha
    user.password = generate_password_hash(new_password)
    
    try:
        db.session.commit()
        return jsonify({'message': 'Senha redefinida com sucesso'}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': 'Erro ao redefinir senha'}), 500


# Rotas de avaliações
@user_bp.route('/submit-rating', methods=['POST'])
def submit_rating():
    if 'user_id' not in session:
        return jsonify({'error': 'Usuário não autenticado'}), 401
    
    data = request.json
    
    # Validar dados obrigatórios
    overall_rating = data.get('overall_rating')
    if not overall_rating or overall_rating < 1 or overall_rating > 5:
        return jsonify({'error': 'Avaliação geral é obrigatória e deve estar entre 1 e 5'}), 400
    
    # Validar outras avaliações (opcionais)
    punctuality_rating = data.get('punctuality_rating', 0)
    cleanliness_rating = data.get('cleanliness_rating', 0)
    comfort_rating = data.get('comfort_rating', 0)
    service_rating = data.get('service_rating', 0)
    
    # Validar se as avaliações estão no range correto
    ratings_to_validate = [punctuality_rating, cleanliness_rating, comfort_rating, service_rating]
    for rating in ratings_to_validate:
        if rating < 0 or rating > 5:
            return jsonify({'error': 'Todas as avaliações devem estar entre 0 e 5'}), 400
    
    # Processar data e hora da viagem
    trip_date = None
    trip_time = None
    
    if data.get('trip_date'):
        try:
            trip_date = datetime.strptime(data['trip_date'], '%Y-%m-%d').date()
        except ValueError:
            return jsonify({'error': 'Formato de data inválido. Use YYYY-MM-DD'}), 400
    
    if data.get('trip_time'):
        try:
            trip_time = datetime.strptime(data['trip_time'], '%H:%M').time()
        except ValueError:
            return jsonify({'error': 'Formato de hora inválido. Use HH:MM'}), 400
    
    # Criar nova avaliação
    rating = Rating(
        user_id=session['user_id'],
        overall_rating=overall_rating,
        punctuality_rating=punctuality_rating,
        cleanliness_rating=cleanliness_rating,
        comfort_rating=comfort_rating,
        service_rating=service_rating,
        comments=data.get('comments', ''),
        bus_line=data.get('bus_line', ''),
        trip_date=trip_date,
        trip_time=trip_time
    )
    
    try:
        db.session.add(rating)
        db.session.commit()
        
        return jsonify({
            'message': 'Avaliação enviada com sucesso',
            'rating': rating.to_dict()
        }), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': 'Erro ao salvar avaliação'}), 500

@user_bp.route('/ratings', methods=['GET'])
def get_user_ratings():
    if 'user_id' not in session:
        return jsonify({'error': 'Usuário não autenticado'}), 401
    
    ratings = Rating.query.filter_by(user_id=session['user_id']).order_by(Rating.created_at.desc()).all()
    return jsonify([rating.to_dict() for rating in ratings])

@user_bp.route('/ratings/stats', methods=['GET'])
def get_ratings_stats():
    """Rota para obter estatísticas gerais das avaliações (para administradores)"""
    # Em uma aplicação real, você verificaria se o usuário é administrador
    
    total_ratings = Rating.query.count()
    if total_ratings == 0:
        return jsonify({
            'total_ratings': 0,
            'average_overall': 0,
            'average_punctuality': 0,
            'average_cleanliness': 0,
            'average_comfort': 0,
            'average_service': 0
        })
    
    # Calcular médias
    from sqlalchemy import func
    
    averages = db.session.query(
        func.avg(Rating.overall_rating).label('avg_overall'),
        func.avg(Rating.punctuality_rating).label('avg_punctuality'),
        func.avg(Rating.cleanliness_rating).label('avg_cleanliness'),
        func.avg(Rating.comfort_rating).label('avg_comfort'),
        func.avg(Rating.service_rating).label('avg_service')
    ).first()
    
    return jsonify({
        'total_ratings': total_ratings,
        'average_overall': round(averages.avg_overall, 2) if averages.avg_overall else 0,
        'average_punctuality': round(averages.avg_punctuality, 2) if averages.avg_punctuality else 0,
        'average_cleanliness': round(averages.avg_cleanliness, 2) if averages.avg_cleanliness else 0,
        'average_comfort': round(averages.avg_comfort, 2) if averages.avg_comfort else 0,
        'average_service': round(averages.avg_service, 2) if averages.avg_service else 0
    })

