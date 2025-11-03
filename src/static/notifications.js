/**
 * Sistema Avançado de Notificações em Tempo Real
 * Mobilidade Urbana - Dashboard
 * 
 * Este arquivo contém todas as funções relacionadas ao sistema de notificações.
 * Pode ser incluído como um script separado para melhor organização do código.
 */

// ============================================================================
// CONFIGURAÇÕES
// ============================================================================

const NOTIFICATION_CONFIG = {
  MIN_BALANCE: 5.00,
  CHECK_BALANCE_INTERVAL: 30000,      // 30 segundos
  CHECK_DELAYS_INTERVAL: 60000,       // 60 segundos
  MAX_NOTIFICATIONS: 50,              // Máximo de notificações armazenadas
  NOTIFICATION_EXPIRY: 7 * 24 * 60 * 60 * 1000, // 7 dias em milissegundos
  STORAGE_KEY: 'notifications',
  ENABLE_SOUND: false,                // Habilitar som de notificação
  ENABLE_DESKTOP_NOTIFICATIONS: true, // Habilitar notificações do navegador
};

// ============================================================================
// VARIÁVEIS GLOBAIS
// ============================================================================

let notifications = [];
let notificationWebSocket = null;
let isWebSocketConnected = false;

// ============================================================================
// CLASSE DE NOTIFICAÇÃO
// ============================================================================

class Notification {
  constructor(title, message, type = 'info', options = {}) {
    this.id = Date.now() + Math.random();
    this.title = title;
    this.message = message;
    this.type = type; // 'line_delay', 'low_balance', 'info', 'success', 'warning', 'error'
    this.time = new Date().toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit' });
    this.read = false;
    this.timestamp = Date.now();
    this.options = options;
  }

  toJSON() {
    return {
      id: this.id,
      title: this.title,
      message: this.message,
      type: this.type,
      time: this.time,
      read: this.read,
      timestamp: this.timestamp,
      options: this.options
    };
  }

  static fromJSON(data) {
    const notification = new Notification(data.title, data.message, data.type, data.options);
    notification.id = data.id;
    notification.time = data.time;
    notification.read = data.read;
    notification.timestamp = data.timestamp;
    return notification;
  }
}

// ============================================================================
// GERENCIADOR DE NOTIFICAÇÕES
// ============================================================================

class NotificationManager {
  constructor() {
    this.notifications = [];
    this.loadFromStorage();
  }

  /**
   * Adicionar uma nova notificação
   */
  add(title, message, type = 'info', options = {}) {
    const notification = new Notification(title, message, type, options);
    this.notifications.unshift(notification);
    
    // Limitar o número de notificações armazenadas
    if (this.notifications.length > NOTIFICATION_CONFIG.MAX_NOTIFICATIONS) {
      this.notifications.pop();
    }
    
    this.saveToStorage();
    this.displayNotification(notification);
    this.updateBadge();
    this.playSound();
    this.showDesktopNotification(notification);
    
    return notification;
  }

  /**
   * Exibir notificação na UI
   */
  displayNotification(notification) {
    const list = document.getElementById('notificationList');
    const noNotificationsMessage = document.getElementById('noNotificationsMessage');
    
    if (noNotificationsMessage && noNotificationsMessage.parentNode) {
      noNotificationsMessage.remove();
    }

    const item = document.createElement('div');
    item.className = `notification-item ${notification.type} ${!notification.read ? 'unread' : ''}`;
    item.dataset.notificationId = notification.id;
    
    const typeIcon = this.getTypeIcon(notification.type);
    
    item.innerHTML = `
      <div class="flex items-start justify-between">
        <div class="flex-1">
          <div class="flex items-center">
            <span class="notification-icon">${typeIcon}</span>
            <p class="notification-title">${this.escapeHtml(notification.title)}</p>
          </div>
          <p class="notification-message">${this.escapeHtml(notification.message)}</p>
          <p class="notification-time">${notification.time}</p>
        </div>
        <button class="notification-close ml-2" data-notification-id="${notification.id}" title="Fechar">
          ✕
        </button>
      </div>
    `;
    
    // Event listener para fechar notificação
    item.querySelector('.notification-close').addEventListener('click', (e) => {
      e.stopPropagation();
      this.remove(notification.id);
      item.remove();
    });
    
    // Event listener para marcar como lida
    item.addEventListener('click', () => {
      this.markAsRead(notification.id);
      item.classList.remove('unread');
    });
    
    if (list) {
      list.prepend(item);
    }
  }

  /**
   * Atualizar badge de notificações não lidas
   */
  updateBadge() {
    const badge = document.getElementById('notificationBadge');
    const unreadCount = this.notifications.filter(n => !n.read).length;
    
    if (badge) {
      if (unreadCount > 0) {
        badge.classList.remove('hidden');
        // Adicionar classe para animar se houver notificações não lidas
        document.getElementById('notificationButton')?.classList.add('has-unread');
      } else {
        badge.classList.add('hidden');
        document.getElementById('notificationButton')?.classList.remove('has-unread');
      }
    }
  }

  /**
   * Marcar notificação como lida
   */
  markAsRead(notificationId) {
    const notification = this.notifications.find(n => n.id === notificationId);
    if (notification) {
      notification.read = true;
      this.saveToStorage();
      this.updateBadge();
    }
  }

  /**
   * Marcar todas as notificações como lidas
   */
  markAllAsRead() {
    this.notifications.forEach(n => n.read = true);
    this.saveToStorage();
    this.updateBadge();
  }

  /**
   * Remover uma notificação
   */
  remove(notificationId) {
    this.notifications = this.notifications.filter(n => n.id !== notificationId);
    this.saveToStorage();
    this.updateBadge();
  }

  /**
   * Limpar notificações expiradas
   */
  clearExpired() {
    const now = Date.now();
    this.notifications = this.notifications.filter(n => 
      (now - n.timestamp) < NOTIFICATION_CONFIG.NOTIFICATION_EXPIRY
    );
    this.saveToStorage();
  }

  /**
   * Salvar notificações no localStorage
   */
  saveToStorage() {
    try {
      const data = this.notifications.map(n => n.toJSON());
      localStorage.setItem(NOTIFICATION_CONFIG.STORAGE_KEY, JSON.stringify(data));
    } catch (error) {
      console.error('Erro ao salvar notificações:', error);
    }
  }

  /**
   * Carregar notificações do localStorage
   */
  loadFromStorage() {
    try {
      const data = localStorage.getItem(NOTIFICATION_CONFIG.STORAGE_KEY);
      if (data) {
        const parsed = JSON.parse(data);
        this.notifications = parsed.map(n => Notification.fromJSON(n));
        this.clearExpired();
      }
    } catch (error) {
      console.error('Erro ao carregar notificações:', error);
    }
  }

  /**
   * Obter ícone do tipo de notificação
   */
  getTypeIcon(type) {
    const icons = {
      'line_delay': '🚌',
      'low_balance': '💳',
      'info': 'ℹ️',
      'success': '✓',
      'warning': '⚠️',
      'error': '✕'
    };
    return icons[type] || 'ℹ️';
  }

  /**
   * Reproduzir som de notificação
   */
  playSound() {
    if (!NOTIFICATION_CONFIG.ENABLE_SOUND) return;
    
    try {
      const audioContext = new (window.AudioContext || window.webkitAudioContext)();
      const oscillator = audioContext.createOscillator();
      const gainNode = audioContext.createGain();
      
      oscillator.connect(gainNode);
      gainNode.connect(audioContext.destination);
      
      oscillator.frequency.value = 800;
      oscillator.type = 'sine';
      
      gainNode.gain.setValueAtTime(0.3, audioContext.currentTime);
      gainNode.gain.exponentialRampToValueAtTime(0.01, audioContext.currentTime + 0.5);
      
      oscillator.start(audioContext.currentTime);
      oscillator.stop(audioContext.currentTime + 0.5);
    } catch (error) {
      console.debug('Erro ao reproduzir som:', error);
    }
  }

  /**
   * Mostrar notificação do navegador (Desktop Notification)
   */
  showDesktopNotification(notification) {
    if (!NOTIFICATION_CONFIG.ENABLE_DESKTOP_NOTIFICATIONS) return;
    
    if ('Notification' in window && Notification.permission === 'granted') {
      try {
        new Notification(notification.title, {
          body: notification.message,
          icon: './img/icone_site.png',
          tag: notification.id
        });
      } catch (error) {
        console.debug('Erro ao mostrar notificação do navegador:', error);
      }
    }
  }

  /**
   * Escapar HTML para evitar XSS
   */
  escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
  }

  /**
   * Obter todas as notificações
   */
  getAll() {
    return this.notifications;
  }

  /**
   * Obter notificações não lidas
   */
  getUnread() {
    return this.notifications.filter(n => !n.read);
  }

  /**
   * Obter notificações por tipo
   */
  getByType(type) {
    return this.notifications.filter(n => n.type === type);
  }

  /**
   * Limpar todas as notificações
   */
  clearAll() {
    this.notifications = [];
    this.saveToStorage();
    this.updateBadge();
  }
}

// ============================================================================
// INSTÂNCIA GLOBAL
// ============================================================================

const notificationManager = new NotificationManager();

// ============================================================================
// FUNÇÕES DE VERIFICAÇÃO
// ============================================================================

/**
 * Verificar saldo baixo
 */
async function checkLowBalance(currentBalance) {
  if (currentBalance < NOTIFICATION_CONFIG.MIN_BALANCE) {
    const title = 'Atenção: Saldo Baixo!';
    const message = `Seu saldo atual é de R$ ${currentBalance.toFixed(2).replace(".", ",")}. Recarregue para evitar interrupções.`;
    
    // Verificar se já foi notificado hoje
    const today = new Date().toDateString();
    const lastNotification = notificationManager.getByType('low_balance').find(n => 
      new Date(n.timestamp).toDateString() === today
    );
    
    if (!lastNotification) {
      notificationManager.add(title, message, 'low_balance');
    }
  }
}

/**
 * Verificar atrasos de linhas
 */
async function checkLineDelays() {
  try {
    // Tentar buscar dados reais da API
    const response = await fetch("/api/lines", {
      method: "GET",
      credentials: "include",
    });
    
    if (response.ok) {
      const data = await response.json();
      
      data.lines?.forEach(line => {
        if (line.delay > 0) {
          const title = `Atraso na ${line.name}`;
          const message = `Motivo: ${line.reason}. Tempo estimado de atraso: ${line.delay} minutos.`;
          
          // Verificar se já foi notificado
          const exists = notificationManager.getByType('line_delay').find(n => 
            n.title === title && (Date.now() - n.timestamp) < 3600000 // 1 hora
          );
          
          if (!exists) {
            notificationManager.add(title, message, 'line_delay');
          }
        }
      });
    }
  } catch (error) {
    console.debug('Erro ao verificar atrasos (usando simulação):', error);
    // Usar simulação se API não estiver disponível
    simulateLineDelays();
  }
}

/**
 * Simular atrasos de linhas (para desenvolvimento)
 */
function simulateLineDelays() {
  const lines = [
    { line: 'Linha 101 - Centro/Bairro', delay: 15, reason: 'Acidente na via', affected: Math.random() > 0.7 },
    { line: 'Linha 205 - Terminal/Universidade', delay: 5, reason: 'Trâfego intenso', affected: Math.random() > 0.8 },
    { line: 'Linha 310 - Industrial/Comercial', delay: 30, reason: 'Problema mecânico', affected: Math.random() > 0.9 }
  ];

  lines.forEach(line => {
    if (line.affected) {
      const title = `Atraso na ${line.line}`;
      const message = `Motivo: ${line.reason}. Tempo estimado de atraso: ${line.delay} minutos.`;
      
      const exists = notificationManager.getByType('line_delay').find(n => 
        n.title === title && (Date.now() - n.timestamp) < 3600000
      );
      
      if (!exists) {
        notificationManager.add(title, message, 'line_delay');
      }
    }
  });
}

// ============================================================================
// WEBSOCKET PARA NOTIFICAÇÕES EM TEMPO REAL
// ============================================================================

/**
 * Conectar ao WebSocket de notificações
 */
function connectWebSocket() {
  try {
    const token = localStorage.getItem('auth_token');
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${protocol}//${window.location.host}/ws/notifications?token=${token}`;
    
    notificationWebSocket = new WebSocket(wsUrl);
    
    notificationWebSocket.onopen = () => {
      console.log('WebSocket conectado');
      isWebSocketConnected = true;
    };
    
    notificationWebSocket.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        
        if (data.type === 'line_delay') {
          const title = `Atraso na ${data.line_name}`;
          const message = `Motivo: ${data.reason}. Tempo estimado de atraso: ${data.delay_minutes} minutos.`;
          notificationManager.add(title, message, 'line_delay');
        } else if (data.type === 'low_balance') {
          const title = 'Atenção: Saldo Baixo!';
          const message = `Seu saldo atual é de R$ ${data.current_balance.toFixed(2).replace(".", ",")}. Recarregue para evitar interrupções.`;
          notificationManager.add(title, message, 'low_balance');
        }
      } catch (error) {
        console.error('Erro ao processar mensagem WebSocket:', error);
      }
    };
    
    notificationWebSocket.onerror = (error) => {
      console.error('Erro no WebSocket:', error);
      isWebSocketConnected = false;
    };
    
    notificationWebSocket.onclose = () => {
      console.log('WebSocket desconectado');
      isWebSocketConnected = false;
      // Tentar reconectar em 5 segundos
      setTimeout(connectWebSocket, 5000);
    };
  } catch (error) {
    console.error('Erro ao conectar WebSocket:', error);
  }
}

// ============================================================================
// INICIALIZAÇÃO
// ============================================================================

/**
 * Inicializar o sistema de notificações
 */
function initializeNotifications() {
  // Solicitar permissão para notificações do navegador
  if ('Notification' in window && Notification.permission === 'default') {
    Notification.requestPermission();
  }
  
  // Carregar notificações salvas
  notificationManager.clearExpired();
  notificationManager.updateBadge();
  
  // Exibir notificações salvas
  notificationManager.getAll().forEach(n => {
    notificationManager.displayNotification(n);
  });
  
  // Configurar event listeners do dropdown
  setupDropdownListeners();
  
  // Conectar ao WebSocket
  connectWebSocket();
  
  // Iniciar verificações periódicas
  setInterval(checkLineDelays, NOTIFICATION_CONFIG.CHECK_DELAYS_INTERVAL);
}

/**
 * Configurar event listeners do dropdown
 */
function setupDropdownListeners() {
  const notificationButton = document.getElementById('notificationButton');
  const notificationDropdown = document.getElementById('notificationDropdown');
  const markAllAsReadButton = document.getElementById('markAllAsRead');

  if (!notificationButton || !notificationDropdown) return;

  // Toggle do dropdown
  notificationButton.addEventListener('click', (event) => {
    event.stopPropagation();
    notificationDropdown.classList.toggle('hidden');
    
    // Marcar todas como lidas ao abrir
    if (!notificationDropdown.classList.contains('hidden')) {
      notificationManager.markAllAsRead();
    }
  });

  // Fechar o dropdown ao clicar fora
  document.addEventListener('click', (event) => {
    if (!notificationDropdown.classList.contains('hidden') && 
        !notificationButton.contains(event.target) &&
        !notificationDropdown.contains(event.target)) {
      notificationDropdown.classList.add('hidden');
    }
  });

  // Marcar todas como lidas (botão)
  if (markAllAsReadButton) {
    markAllAsReadButton.addEventListener('click', () => {
      notificationManager.markAllAsRead();
      notificationDropdown.classList.add('hidden');
    });
  }

  // Fechar ao pressionar ESC
  document.addEventListener('keydown', (event) => {
    if (event.key === 'Escape' && !notificationDropdown.classList.contains('hidden')) {
      notificationDropdown.classList.add('hidden');
    }
  });
}

// ============================================================================
// EXPORTAR PARA USO GLOBAL
// ============================================================================

window.NotificationSystem = {
  manager: notificationManager,
  add: (title, message, type, options) => notificationManager.add(title, message, type, options),
  markAsRead: (id) => notificationManager.markAsRead(id),
  markAllAsRead: () => notificationManager.markAllAsRead(),
  remove: (id) => notificationManager.remove(id),
  clearAll: () => notificationManager.clearAll(),
  getAll: () => notificationManager.getAll(),
  getUnread: () => notificationManager.getUnread(),
  getByType: (type) => notificationManager.getByType(type),
  initialize: initializeNotifications,
  checkLowBalance: checkLowBalance,
  checkLineDelays: checkLineDelays,
  connectWebSocket: connectWebSocket,
};

// ============================================================================
// INICIALIZAR QUANDO O DOM ESTIVER PRONTO
// ============================================================================

if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', initializeNotifications);
} else {
  initializeNotifications();
}
