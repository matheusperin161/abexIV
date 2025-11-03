"""
Exemplo de Integração do Sistema de Notificações com Backend FastAPI

Este arquivo demonstra como integrar o sistema de notificações frontend
com endpoints do backend para fornecer dados reais de atrasos e saldo.
"""

from fastapi import FastAPI, Depends, HTTPException, WebSocket
from fastapi.responses import JSONResponse
from sqlalchemy import Column, Integer, String, Float, DateTime, Boolean
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
import json
import asyncio
from typing import List, Optional

# ============================================================================
# MODELOS DE BANCO DE DADOS
# ============================================================================

class UserLine(Base):
    """Modelo para armazenar as linhas que um usuário costuma usar"""
    __tablename__ = "user_lines"
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    line_id = Column(Integer, ForeignKey("transit_lines.id"))
    created_at = Column(DateTime, default=datetime.utcnow)


class TransitLine(Base):
    """Modelo para armazenar informações das linhas de transporte"""
    __tablename__ = "transit_lines"
    
    id = Column(Integer, primary_key=True)
    name = Column(String(100), unique=True)
    description = Column(String(255))
    current_delay = Column(Integer, default=0)  # em minutos
    delay_reason = Column(String(255), nullable=True)
    updated_at = Column(DateTime, default=datetime.utcnow)


class NotificationLog(Base):
    """Modelo para armazenar histórico de notificações"""
    __tablename__ = "notification_logs"
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    notification_type = Column(String(50))  # 'line_delay' ou 'low_balance'
    title = Column(String(255))
    message = Column(String(500))
    read = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)


# ============================================================================
# ENDPOINTS DE NOTIFICAÇÕES
# ============================================================================

@app.get("/api/lines")
async def get_user_lines(current_user = Depends(get_current_user), db: Session = Depends(get_db)):
    """
    Retorna as linhas que o usuário costuma utilizar com informações de atraso.
    
    Resposta:
    {
        "lines": [
            {
                "id": 101,
                "name": "Linha 101 - Centro/Bairro",
                "delay": 15,
                "reason": "Acidente na via"
            },
            {
                "id": 205,
                "name": "Linha 205 - Terminal/Universidade",
                "delay": 0,
                "reason": null
            }
        ]
    }
    """
    try:
        # Buscar linhas do usuário
        user_lines = db.query(UserLine).filter(
            UserLine.user_id == current_user.id
        ).all()
        
        lines_data = []
        for user_line in user_lines:
            transit_line = db.query(TransitLine).filter(
                TransitLine.id == user_line.line_id
            ).first()
            
            if transit_line:
                lines_data.append({
                    "id": transit_line.id,
                    "name": transit_line.name,
                    "delay": transit_line.current_delay,
                    "reason": transit_line.delay_reason
                })
        
        return JSONResponse({
            "lines": lines_data
        })
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/notifications")
async def get_notifications(current_user = Depends(get_current_user), db: Session = Depends(get_db)):
    """
    Retorna o histórico de notificações do usuário.
    
    Resposta:
    {
        "notifications": [
            {
                "id": 1,
                "title": "Atraso na Linha 101 - Centro/Bairro",
                "message": "Motivo: Acidente na via. Tempo estimado de atraso: 15 minutos.",
                "type": "line_delay",
                "read": false,
                "created_at": "2024-11-03T14:30:00"
            }
        ]
    }
    """
    try:
        # Buscar notificações dos últimos 7 dias
        seven_days_ago = datetime.utcnow() - timedelta(days=7)
        
        notifications = db.query(NotificationLog).filter(
            NotificationLog.user_id == current_user.id,
            NotificationLog.created_at >= seven_days_ago
        ).order_by(NotificationLog.created_at.desc()).all()
        
        notifications_data = [{
            "id": n.id,
            "title": n.title,
            "message": n.message,
            "type": n.notification_type,
            "read": n.read,
            "created_at": n.created_at.isoformat()
        } for n in notifications]
        
        return JSONResponse({
            "notifications": notifications_data
        })
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/notifications/{notification_id}/read")
async def mark_notification_read(
    notification_id: int,
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Marca uma notificação como lida.
    """
    try:
        notification = db.query(NotificationLog).filter(
            NotificationLog.id == notification_id,
            NotificationLog.user_id == current_user.id
        ).first()
        
        if not notification:
            raise HTTPException(status_code=404, detail="Notificação não encontrada")
        
        notification.read = True
        db.commit()
        
        return JSONResponse({"status": "success"})
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/notifications/mark-all-read")
async def mark_all_notifications_read(
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Marca todas as notificações do usuário como lidas.
    """
    try:
        db.query(NotificationLog).filter(
            NotificationLog.user_id == current_user.id,
            NotificationLog.read == False
        ).update({"read": True})
        
        db.commit()
        
        return JSONResponse({"status": "success"})
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# WEBSOCKET PARA NOTIFICAÇÕES EM TEMPO REAL
# ============================================================================

class NotificationManager:
    """Gerenciador de conexões WebSocket para notificações em tempo real"""
    
    def __init__(self):
        self.active_connections: dict = {}
    
    async def connect(self, websocket: WebSocket, user_id: int):
        """Conectar um usuário ao WebSocket"""
        await websocket.accept()
        if user_id not in self.active_connections:
            self.active_connections[user_id] = []
        self.active_connections[user_id].append(websocket)
    
    def disconnect(self, user_id: int, websocket: WebSocket):
        """Desconectar um usuário do WebSocket"""
        if user_id in self.active_connections:
            self.active_connections[user_id].remove(websocket)
            if not self.active_connections[user_id]:
                del self.active_connections[user_id]
    
    async def broadcast_to_user(self, user_id: int, message: dict):
        """Enviar mensagem para todas as conexões de um usuário"""
        if user_id in self.active_connections:
            for connection in self.active_connections[user_id]:
                try:
                    await connection.send_json(message)
                except Exception as e:
                    print(f"Erro ao enviar mensagem: {e}")
    
    async def broadcast_to_all(self, message: dict):
        """Enviar mensagem para todos os usuários conectados"""
        for user_id in self.active_connections:
            await self.broadcast_to_user(user_id, message)


notification_manager = NotificationManager()


@app.websocket("/ws/notifications")
async def websocket_notifications(websocket: WebSocket, token: str = Query(None)):
    """
    WebSocket para notificações em tempo real.
    
    Mensagens que podem ser recebidas:
    
    1. Atraso de Linha:
    {
        "type": "line_delay",
        "line_id": 101,
        "line_name": "Linha 101 - Centro/Bairro",
        "delay_minutes": 15,
        "reason": "Acidente na via"
    }
    
    2. Saldo Baixo:
    {
        "type": "low_balance",
        "current_balance": 3.50,
        "min_balance": 5.00
    }
    """
    try:
        # Validar token e obter usuário
        current_user = await get_current_user_from_token(token)
        
        # Conectar ao WebSocket
        await notification_manager.connect(websocket, current_user.id)
        
        # Manter conexão aberta
        while True:
            data = await websocket.receive_text()
            # Processar mensagens do cliente se necessário
            
    except Exception as e:
        print(f"Erro no WebSocket: {e}")
    finally:
        notification_manager.disconnect(current_user.id, websocket)


# ============================================================================
# SERVIÇO DE MONITORAMENTO DE ATRASOS
# ============================================================================

async def monitor_line_delays(db: Session):
    """
    Serviço que monitora atrasos nas linhas e envia notificações.
    Deve ser executado como uma tarefa assíncrona em background.
    """
    while True:
        try:
            # Buscar todas as linhas
            lines = db.query(TransitLine).all()
            
            for line in lines:
                # Aqui você faria uma chamada para uma API externa
                # que fornece informações de atraso em tempo real
                # Por exemplo: API de transporte público, GPS dos ônibus, etc.
                
                # Simular verificação de atraso
                previous_delay = line.current_delay
                # new_delay = await fetch_real_time_delay(line.id)
                
                # Se houve mudança no atraso, notificar usuários
                # if new_delay != previous_delay:
                #     await notify_users_about_line_delay(line, new_delay)
                
                pass
            
            # Aguardar 60 segundos antes da próxima verificação
            await asyncio.sleep(60)
        
        except Exception as e:
            print(f"Erro ao monitorar atrasos: {e}")
            await asyncio.sleep(60)


async def notify_users_about_line_delay(
    db: Session,
    line: TransitLine,
    delay_minutes: int,
    reason: str
):
    """
    Notifica todos os usuários que seguem uma linha sobre atraso.
    """
    try:
        # Buscar todos os usuários que seguem esta linha
        user_lines = db.query(UserLine).filter(
            UserLine.line_id == line.id
        ).all()
        
        for user_line in user_lines:
            # Criar notificação no banco de dados
            notification = NotificationLog(
                user_id=user_line.user_id,
                notification_type="line_delay",
                title=f"Atraso na {line.name}",
                message=f"Motivo: {reason}. Tempo estimado de atraso: {delay_minutes} minutos.",
                read=False
            )
            db.add(notification)
            
            # Enviar via WebSocket se usuário estiver conectado
            await notification_manager.broadcast_to_user(
                user_line.user_id,
                {
                    "type": "line_delay",
                    "line_id": line.id,
                    "line_name": line.name,
                    "delay_minutes": delay_minutes,
                    "reason": reason
                }
            )
        
        db.commit()
    
    except Exception as e:
        print(f"Erro ao notificar usuários: {e}")
        db.rollback()


# ============================================================================
# SERVIÇO DE MONITORAMENTO DE SALDO BAIXO
# ============================================================================

async def monitor_low_balance(db: Session):
    """
    Serviço que monitora saldo baixo dos usuários.
    Deve ser executado como uma tarefa assíncrona em background.
    """
    MIN_BALANCE = 5.00
    
    while True:
        try:
            # Buscar todos os usuários
            users = db.query(User).all()
            
            for user in users:
                # Verificar se saldo está abaixo do mínimo
                if user.balance < MIN_BALANCE:
                    # Verificar se já foi notificado hoje
                    today = datetime.utcnow().date()
                    existing_notification = db.query(NotificationLog).filter(
                        NotificationLog.user_id == user.id,
                        NotificationLog.notification_type == "low_balance",
                        NotificationLog.created_at >= datetime.combine(today, datetime.min.time())
                    ).first()
                    
                    if not existing_notification:
                        # Criar notificação
                        notification = NotificationLog(
                            user_id=user.id,
                            notification_type="low_balance",
                            title="Atenção: Saldo Baixo!",
                            message=f"Seu saldo atual é de R$ {user.balance:.2f}. Recarregue para evitar interrupções.",
                            read=False
                        )
                        db.add(notification)
                        
                        # Enviar via WebSocket se usuário estiver conectado
                        await notification_manager.broadcast_to_user(
                            user.id,
                            {
                                "type": "low_balance",
                                "current_balance": user.balance,
                                "min_balance": MIN_BALANCE
                            }
                        )
            
            db.commit()
            
            # Aguardar 30 segundos antes da próxima verificação
            await asyncio.sleep(30)
        
        except Exception as e:
            print(f"Erro ao monitorar saldo: {e}")
            await asyncio.sleep(30)


# ============================================================================
# INICIALIZAÇÃO DO APLICATIVO
# ============================================================================

@app.on_event("startup")
async def startup_event():
    """Iniciar tarefas de background ao iniciar a aplicação"""
    # Iniciar monitoramento de atrasos
    asyncio.create_task(monitor_line_delays(SessionLocal()))
    
    # Iniciar monitoramento de saldo baixo
    asyncio.create_task(monitor_low_balance(SessionLocal()))


# ============================================================================
# EXEMPLO DE USO NO FRONTEND
# ============================================================================

"""
// JavaScript no frontend para usar os novos endpoints

// 1. Carregar linhas do usuário
async function loadUserLines() {
    try {
        const response = await fetch("/api/lines", {
            method: "GET",
            credentials: "include",
        });
        
        if (response.ok) {
            const data = await response.json();
            console.log("Linhas do usuário:", data.lines);
            // Atualizar UI com as linhas
        }
    } catch (error) {
        console.error("Erro ao carregar linhas:", error);
    }
}

// 2. Conectar ao WebSocket para notificações em tempo real
function connectWebSocket() {
    const token = localStorage.getItem('auth_token');
    const ws = new WebSocket(`ws://localhost:8000/ws/notifications?token=${token}`);
    
    ws.onmessage = function(event) {
        const notification = JSON.parse(event.data);
        
        if (notification.type === 'line_delay') {
            addNotification(
                `Atraso na ${notification.line_name}`,
                `Motivo: ${notification.reason}. Tempo estimado de atraso: ${notification.delay_minutes} minutos.`,
                'line_delay'
            );
        } else if (notification.type === 'low_balance') {
            addNotification(
                'Atenção: Saldo Baixo!',
                `Seu saldo atual é de R$ ${notification.current_balance.toFixed(2).replace(".", ",")}. Recarregue para evitar interrupções.`,
                'low_balance'
            );
        }
    };
    
    ws.onerror = function(error) {
        console.error("WebSocket error:", error);
    };
}

// 3. Marcar notificação como lida
async function markNotificationAsRead(notificationId) {
    try {
        const response = await fetch(`/api/notifications/${notificationId}/read`, {
            method: "POST",
            credentials: "include",
        });
        
        if (response.ok) {
            console.log("Notificação marcada como lida");
        }
    } catch (error) {
        console.error("Erro ao marcar notificação como lida:", error);
    }
}

// 4. Marcar todas as notificações como lidas
async function markAllNotificationsAsRead() {
    try {
        const response = await fetch("/api/notifications/mark-all-read", {
            method: "POST",
            credentials: "include",
        });
        
        if (response.ok) {
            console.log("Todas as notificações marcadas como lidas");
        }
    } catch (error) {
        console.error("Erro ao marcar notificações como lidas:", error);
    }
}
"""

# ============================================================================
# NOTAS IMPORTANTES
# ============================================================================

"""
1. Este é um exemplo de implementação. Adapte conforme sua arquitetura.

2. Certifique-se de implementar autenticação adequada nos endpoints.

3. Use HTTPS em produção, especialmente para WebSocket (WSS).

4. Implemente rate limiting para evitar abuso de API.

5. Considere usar um message broker (Redis, RabbitMQ) para escalar
   as notificações em produção.

6. Implemente logging adequado para debugging.

7. Teste os endpoints com ferramentas como Postman ou Thunder Client.

8. Considere implementar testes unitários para os endpoints.

9. Para produção, use um servidor ASGI como Uvicorn ou Gunicorn.

10. Implemente CORS adequadamente se o frontend estiver em domínio diferente.
"""
