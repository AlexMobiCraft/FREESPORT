#!/bin/bash

# Скрипт первоначальной настройки сервера для FREESPORT Platform
# Настройка сервера 5.35.124.149 для домена freesport.ru

set -e

# Цвета для вывода
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Конфигурация
REPO_URL="https://github.com/AlexMobiCraft/FREESPORT.git"
DOMAIN="freesport.ru"
SERVER_IP="5.35.124.149"
PROJECT_DIR="/opt/freesport"

# Функция вывода сообщений
log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

log_step() {
    echo -e "${BLUE}[STEP]${NC} $1"
}

# Проверка прав root
check_root() {
    if [[ $EUID -ne 0 ]]; then
        log_error "Этот скрипт должен быть запущен с правами root"
        echo "Используйте: sudo $0"
        exit 1
    fi
}

# Настройка имени хоста
setup_hostname() {
    log_step "Настройка имени хоста..."
    
    # Получаем текущее имя хоста
    CURRENT_HOSTNAME=$(hostname)
    
    # Установка имени хоста с проверкой
    if hostnamectl set-hostname freesport-server; then
        log_info "Имя хоста установлено: freesport-server"
        
        # Добавление в /etc/hosts для разрешения имени
        if ! grep -q "freesport-server" /etc/hosts; then
            echo "127.0.1.1 freesport-server" >> /etc/hosts
        fi
        
        # Добавление домена в /etc/hosts
        if ! grep -q "$DOMAIN" /etc/hosts; then
            echo "$SERVER_IP $DOMAIN www.$DOMAIN" >> /etc/hosts
        fi
    else
        log_warn "Не удалось изменить имя хоста, используем текущее: $CURRENT_HOSTNAME"
        
        # Добавляем текущее имя хоста в /etc/hosts
        if ! grep -q "$CURRENT_HOSTNAME" /etc/hosts; then
            echo "127.0.1.1 $CURRENT_HOSTNAME" >> /etc/hosts
        fi
        
        # Добавление домена в /etc/hosts
        if ! grep -q "$DOMAIN" /etc/hosts; then
            echo "$SERVER_IP $DOMAIN www.$DOMAIN" >> /etc/hosts
        fi
    fi
}

# Обновление системы
update_system() {
    log_step "Обновление системы..."
    
    apt update && apt upgrade -y
    apt install -y curl wget gnupg lsb-release software-properties-common ca-certificates git htop tree ncdu
    
    log_info "Система обновлена"
}

# Установка Docker
install_docker() {
    log_step "Установка Docker..."
    
    # Удаление старых версий
    apt remove -y docker docker-engine docker.io containerd runc || true
    
    # Добавление официального GPG ключа Docker
    mkdir -m 0755 -p /etc/apt/keyrings
    curl -fsSL https://download.docker.com/linux/ubuntu/gpg | gpg --dearmor -o /etc/apt/keyrings/docker.gpg
    
    # Добавление репозитория Docker
    echo \
      "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu \
      $(. /etc/os-release && echo "$VERSION_CODENAME") stable" | \
      tee /etc/apt/sources.list.d/docker.list > /dev/null
    
    # Установка Docker Engine
    apt update
    apt install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
    
    # Запуск Docker
    systemctl start docker
    systemctl enable docker
    
    log_info "Docker установлен"
}

# Создание пользователя для развертывания
create_deploy_user() {
    log_step "Создание пользователя для развертывания..."
    
    if ! id "freesport" &>/dev/null; then
        # Создаем системного пользователя с домашней директорией
        adduser --system --group --home /opt/freesport --shell /bin/bash freesport
        
        # Добавляем в группы
        usermod -aG sudo,docker freesport
        
        # Настройка sudo без пароля для пользователя freesport
        echo "freesport ALL=(ALL) NOPASSWD:ALL" >> /etc/sudoers.d/freesport
        
        log_info "Пользователь freesport создан"
    else
        log_warn "Пользователь freesport уже существует"
    fi
    
    # Убеждаемся, что домашняя директория существует и имеет правильные права
    if [ ! -d "/opt/freesport" ]; then
        mkdir -p /opt/freesport
    fi
    
    chown freesport:freesport /opt/freesport
    
    # Создаем необходимые директории
    mkdir -p /opt/freesport/{data,logs,backups}
    chown -R freesport:freesport /opt/freesport
    
    log_info "Директория проекта настроена: /opt/freesport"
}

# Настройка файрвола
setup_firewall() {
    log_step "Настройка файрвола..."
    
    # Настройка UFW
    ufw --force reset
    ufw default deny incoming
    ufw default allow outgoing
    
    # Разрешение необходимых портов
    ufw allow 22/tcp    # SSH
    ufw allow 80/tcp    # HTTP
    ufw allow 443/tcp   # HTTPS
    
    ufw --force enable
    
    log_info "Файрвол настроен"
}

# Настройка SSH
setup_ssh() {
    log_step "Настройка SSH..."
    
    # Резервное копирование оригинального конфигурационного файла
    cp /etc/ssh/sshd_config /etc/ssh/sshd_config.backup
    
    # Настройка SSH
    sed -i 's/#PermitRootLogin yes/PermitRootLogin no/' /etc/ssh/sshd_config
    sed -i 's/#PasswordAuthentication yes/PasswordAuthentication no/' /etc/ssh/sshd_config
    sed -i 's/#PubkeyAuthentication yes/PubkeyAuthentication yes/' /etc/ssh/sshd_config
    
    # Перезапуск SSH
    systemctl restart ssh
    
    log_info "SSH настроен"
    log_warn "Root доступ по SSH отключен. Используйте ключи для аутентификации."
}

# Клонирование и настройка проекта
setup_project() {
    log_step "Настройка проекта..."
    
    # Создание директории для проекта
    mkdir -p $PROJECT_DIR
    chown freesport:freesport $PROJECT_DIR
    
    # Клонирование проекта
    cd $PROJECT_DIR
    sudo -u freesport git clone $REPO_URL .
    
    # Установка прав на выполнение скриптов
    sudo -u freesport chmod +x scripts/deploy/*.sh
    
    # Создание файла окружения
    sudo -u freesport cp .env.prod.example .env.prod
    
    # Настройка переменных окружения
    sudo -u freesport sed -i "s/yourdomain.com/$DOMAIN/g" .env.prod
    sudo -u freesport sed -i "s/your-super-secret-key-change-this-in-production/$(openssl rand -base64 32)/g" .env.prod
    sudo -u freesport sed -i "s/change-this-secure-password/$(openssl rand -base64 16)/g" .env.prod
    sudo -u freesport sed -i "s/change-this-redis-password/$(openssl rand -base64 16)/g" .env.prod
    
    log_info "Проект настроен в $PROJECT_DIR"
    log_warn "Проверьте и отредактируйте файл $PROJECT_DIR/.env.prod при необходимости"
}

# Настройка автоматического обновления
setup_auto_update() {
    log_step "Настройка автоматического обновления..."
    
    # Создание скрипта обновления
    cat > /usr/local/bin/freesport-update << EOF
#!/bin/bash
cd $PROJECT_DIR
sudo -u freesport ./scripts/deploy/deploy.sh update
EOF
    
    chmod +x /usr/local/bin/freesport-update
    
    # Создание скрипта резервного копирования
    cat > /usr/local/bin/freesport-backup << EOF
#!/bin/bash
cd $PROJECT_DIR
sudo -u freesport ./scripts/deploy/deploy.sh backup
EOF
    
    chmod +x /usr/local/bin/freesport-backup
    
    # Добавление в cron
    (sudo -u freesport crontab -l 2>/dev/null; echo "0 3 * * * /usr/local/bin/freesport-update") | sudo -u freesport crontab -
    (sudo -u freesport crontab -l 2>/dev/null; echo "0 2 * * * /usr/local/bin/freesport-backup") | sudo -u freesport crontab -
    
    log_info "Автоматическое обновление настроено"
}

# Настройка логирования
setup_logging() {
    log_step "Настройка логирования..."
    
    # Создание директории для логов
    mkdir -p /var/log/freesport
    chown freesport:freesport /var/log/freesport
    
    # Настройка ротации логов
    cat > /etc/logrotate.d/freesport << EOF
/var/log/freesport/*.log {
    daily
    missingok
    rotate 30
    compress
    delaycompress
    notifempty
    create 644 freesport freesport
    postrotate
        cd $PROJECT_DIR && sudo -u freesport docker compose -f docker-compose.prod.yml restart nginx
    endscript
}
EOF
    
    log_info "Логирование настроено"
}

# Первоначальное развертывание
initial_deploy() {
    log_step "Первичное развертывание..."
    
    cd $PROJECT_DIR
    sudo -u freesport ./scripts/deploy/deploy.sh init
    
    log_info "Первичное развертывание завершено"
}

# Показать следующие шаги
show_next_steps() {
    log_info "Настройка сервера завершена!"
    echo ""
    echo "========================================"
    echo "  ИНФОРМАЦИЯ О РАЗВЕРТЫВАНИИ"
    echo "========================================"
    echo "Домен: $DOMAIN"
    echo "IP адрес: $SERVER_IP"
    echo "Директория проекта: $PROJECT_DIR"
    echo "Пользователь: freesport"
    echo ""
    echo "Следующие шаги:"
    echo "1. Переключитесь на пользователя freesport:"
    echo "   su - freesport"
    echo ""
    echo "2. Проверьте файл окружения:"
    echo "   nano $PROJECT_DIR/.env.prod"
    echo ""
    echo "3. Запустите развертывание (если не было выполнено автоматически):"
    echo "   cd $PROJECT_DIR"
    echo "   ./scripts/deploy/deploy.sh init"
    echo ""
    echo "4. Настройте SSL сертификат:"
    echo "   sudo certbot --nginx -d $DOMAIN -d www.$DOMAIN"
    echo ""
    echo "5. Проверьте работу сайта:"
    echo "   curl https://$DOMAIN"
    echo ""
    echo "Полезные команды:"
    echo "- Статус сервисов: cd $PROJECT_DIR && ./scripts/deploy/deploy.sh status"
    echo "- Просмотр логов: cd $PROJECT_DIR && docker compose -f docker/docker-compose.prod.yml logs -f"
    echo "- Обновление: cd $PROJECT_DIR && ./scripts/deploy/deploy.sh update"
    echo ""
    echo "Важные файлы:"
    echo "- Конфигурация: $PROJECT_DIR/.env.prod"
    echo "- Логи: /var/log/freesport/"
    echo "- Данные: $PROJECT_DIR/data/"
    echo ""
    log_warn "Не забудьте настроить DNS запись для домена $DOMAIN на IP $SERVER_IP"
}

# Основная функция
main() {
    echo "========================================"
    echo "  Первоначальная настройка сервера для"
    echo "  FREESPORT Platform"
    echo "========================================"
    echo "Домен: $DOMAIN"
    echo "IP: $SERVER_IP"
    echo "Репозиторий: $REPO_URL"
    echo ""
    
    check_root
    setup_hostname
    update_system
    install_docker
    create_deploy_user
    setup_firewall
    setup_ssh
    setup_project
    setup_logging
    setup_auto_update
    
    # Запрос на выполнение развертывания
    read -p "Выполнить первоначальное развертывание? (y/n): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        initial_deploy
    fi
    
    show_next_steps
    
    echo ""
    log_info "Настройка сервера завершена!"
}

# Запуск основной функции
main "$@"