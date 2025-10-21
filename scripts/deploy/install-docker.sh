#!/bin/bash

# Скрипт автоматической установки Docker и Docker Compose
# Поддерживаемые ОС: Ubuntu 20.04+, Debian 11+, CentOS 8+, RHEL 8+

set -e

# Цвета для вывода
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

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

# Определение ОС
detect_os() {
    if [ -f /etc/os-release ]; then
        . /etc/os-release
        OS=$NAME
        VER=$VERSION_ID
    else
        log_error "Не удалось определить операционную систему"
        exit 1
    fi
    
    log_info "Обнаружена ОС: $OS $VER"
}

# Обновление системы
update_system() {
    log_step "Обновление системы..."
    
    if [[ "$OS" == *"Ubuntu"* ]] || [[ "$OS" == *"Debian"* ]]; then
        apt update && apt upgrade -y
        apt install -y curl wget gnupg lsb-release software-properties-common ca-certificates
    elif [[ "$OS" == *"CentOS"* ]] || [[ "$OS" == *"Red Hat"* ]] || [[ "$OS" == *"Rocky"* ]]; then
        yum update -y
        yum install -y curl wget gnupl
    else
        log_error "Неподдерживаемая операционная система: $OS"
        exit 1
    fi
    
    log_info "Система обновлена"
}

# Установка Docker
install_docker() {
    log_step "Установка Docker..."
    
    if [[ "$OS" == *"Ubuntu"* ]] || [[ "$OS" == *"Debian"* ]]; then
        # Удаление старых версий Docker
        apt remove -y docker docker-engine docker.io containerd runc || true
        
        # Добавление официального GPG ключа Docker
        mkdir -m 0755 -p /etc/apt/keyrings
        curl -fsSL https://download.docker.com/linux/$ID/gpg | gpg --dearmor -o /etc/apt/keyrings/docker.gpg
        
        # Добавление репозитория Docker
        echo \
          "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/$ID \
          $(. /etc/os-release && echo "$VERSION_CODENAME") stable" | \
          tee /etc/apt/sources.list.d/docker.list > /dev/null
        
        # Установка Docker Engine
        apt update
        apt install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
        
    elif [[ "$OS" == *"CentOS"* ]] || [[ "$OS" == *"Red Hat"* ]] || [[ "$OS" == *"Rocky"* ]]; then
        # Удаление старых версий Docker
        yum remove -y docker docker-client docker-client-latest docker-common docker-latest docker-latest-logrotate docker-logrotate docker-engine || true
        
        # Добавление репозитория Docker
        yum install -y yum-utils
        yum-config-manager --add-repo https://download.docker.com/linux/centos/docker-ce.repo
        
        # Установка Docker Engine
        yum install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
    fi
    
    log_info "Docker установлен"
}

# Запуск и настройка Docker
configure_docker() {
    log_step "Настройка Docker..."
    
    # Запуск Docker
    systemctl start docker
    systemctl enable docker
    
    # Добавление текущего пользователя в группу docker
    if [ -n "$SUDO_USER" ]; then
        usermod -aG docker "$SUDO_USER"
        log_info "Пользователь $SUDO_USER добавлен в группу docker"
        log_warn "Для применения изменений необходимо перелогиниться или выполнить: newgrp docker"
    fi
    
    # Проверка установки
    docker_version=$(docker --version)
    compose_version=$(docker compose version)
    
    log_info "Версия Docker: $docker_version"
    log_info "Версия Docker Compose: $compose_version"
}

# Установка Docker Compose standalone (если плагин не установлен)
install_docker_compose_standalone() {
    if ! command -v docker-compose &> /dev/null; then
        log_step "Установка Docker Compose standalone..."
        
        # Получение последней версии
        COMPOSE_VERSION=$(curl -s https://api.github.com/repos/docker/compose/releases/latest | grep tag_name | cut -d '"' -f 4)
        
        # Скачивание и установка
        curl -L "https://github.com/docker/compose/releases/download/${COMPOSE_VERSION}/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
        chmod +x /usr/local/bin/docker-compose
        
        log_info "Docker Compose standalone установлен: $(docker-compose --version)"
    else
        log_info "Docker Compose уже установлен: $(docker-compose --version)"
    fi
}

# Настройка файрвола
configure_firewall() {
    log_step "Настройка файрвола..."
    
    if command -v ufw &> /dev/null; then
        # Ubuntu/Debian
        ufw allow 22/tcp
        ufw allow 80/tcp
        ufw allow 443/tcp
        if ! ufw status | grep -q "Status: active"; then
            ufw --force enable
        fi
        log_info "UFW настроен"
    elif command -v firewall-cmd &> /dev/null; then
        # CentOS/RHEL
        systemctl enable firewalld
        systemctl start firewalld
        firewall-cmd --permanent --add-service=ssh
        firewall-cmd --permanent --add-service=http
        firewall-cmd --permanent --add-service=https
        firewall-cmd --reload
        log_info "Firewalld настроен"
    else
        log_warn "Файрвол не найден. Рекомендуется настроить его вручную."
    fi
}

# Оптимизация Docker
optimize_docker() {
    log_step "Оптимизация Docker..."
    
    # Создание конфигурации Docker daemon
    mkdir -p /etc/docker
    cat > /etc/docker/daemon.json << EOF
{
  "log-driver": "json-file",
  "log-opts": {
    "max-size": "10m",
    "max-file": "3"
  },
  "storage-driver": "overlay2",
  "default-ulimits": {
    "nofile": {
      "Name": "nofile",
      "Hard": 64000,
      "Soft": 64000
    }
  },
  "live-restore": true,
  "userland-proxy": false,
  "experimental": false
}
EOF
    
    # Перезапуск Docker
    systemctl restart docker
    
    log_info "Docker оптимизирован"
}

# Установка дополнительных утилит
install_additional_tools() {
    log_step "Установка дополнительных утилит..."
    
    if [[ "$OS" == *"Ubuntu"* ]] || [[ "$OS" == *"Debian"* ]]; then
        apt install -y git htop tree ncdu
    elif [[ "$OS" == *"CentOS"* ]] || [[ "$OS" == *"Red Hat"* ]] || [[ "$OS" == *"Rocky"* ]]; then
        yum install -y git htop tree ncdu
    fi
    
    log_info "Дополнительные утилиты установлены"
}

# Проверка установки
verify_installation() {
    log_step "Проверка установки..."
    
    # Проверка Docker
    if docker run --rm hello-world > /dev/null 2>&1; then
        log_info "✓ Docker работает корректно"
    else
        log_error "✗ Docker не работает корректно"
        exit 1
    fi
    
    # Проверка Docker Compose
    if docker compose version > /dev/null 2>&1; then
        log_info "✓ Docker Compose работает корректно"
    else
        log_error "✗ Docker Compose не работает корректно"
        exit 1
    fi
    
    log_info "Проверка завершена успешно!"
}

# Показать следующие шаги
show_next_steps() {
    log_info "Установка Docker завершена успешно!"
    echo ""
    echo "Следующие шаги:"
    echo "1. Если вы не root пользователь, перелогиньтесь для применения изменений группы docker"
    echo "2. Клонируйте репозиторий проекта:"
    echo "   git clone https://github.com/AlexMobiCraft/FREESPORT.git freesport"
    echo "   cd freesport"
    echo "3. Настройте переменные окружения:"
    echo "   cp .env.prod.example .env.prod"
    echo "   nano .env.prod"
    echo "4. Разверните проект:"
    echo "   chmod +x scripts/deploy/*.sh"
    echo "   ./scripts/deploy/deploy.sh init"
    echo ""
    echo "Полезные команды:"
    echo "- docker ps                    # Показать запущенные контейнеры"
    echo "- docker logs <container>      # Показать логи контейнера"
    echo "- docker system prune          # Очистить систему Docker"
    echo ""
    echo "Документация:"
    echo "- Быстрое развертывание: docs/deploy/quick-deployment.md"
    echo "- Полная инструкция: docs/deploy/docker-server-setup.md"
}

# Основная функция
main() {
    echo "========================================"
    echo "  Установка Docker и Docker Compose"
    echo "========================================"
    echo ""
    
    check_root
    detect_os
    update_system
    install_docker
    configure_docker
    install_docker_compose_standalone
    configure_firewall
    optimize_docker
    install_additional_tools
    verify_installation
    show_next_steps
    
    echo ""
    log_info "Установка завершена!"
}

# Запуск основной функции
main "$@"