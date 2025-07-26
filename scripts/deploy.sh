#!/bin/bash
# =============================================================================
# Car Auction Analyzer - Production Deployment Script
# =============================================================================
# This script automates the deployment of the Car Auction Analyzer application
# to production environments. It handles environment validation, Docker image
# building and pushing, database migrations, service deployment, and includes
# health checks with rollback capabilities.
#
# Usage: ./deploy.sh [options]
#   Options:
#     -e, --environment ENV    Deployment environment (staging|production)
#     -t, --tag TAG            Docker image tag (default: date-based)
#     -s, --skip-build         Skip building images
#     -f, --force              Force deployment without confirmation
#     -h, --help               Show this help message
#
# Example: ./deploy.sh --environment production --tag v1.2.3
# =============================================================================

set -e  # Exit immediately if a command exits with a non-zero status

# ===== CONFIGURATION =====
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
DOCKER_COMPOSE_FILE="docker-compose.prod.yml"
ENV_FILE=".env.production"
LOG_FILE="deployment_$(date +%Y%m%d_%H%M%S).log"
DEFAULT_TAG="$(date +%Y%m%d_%H%M)"
DEPLOYMENT_TIMEOUT=300  # 5 minutes timeout for deployment

# ===== COLORS FOR OUTPUT =====
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# ===== FUNCTIONS =====

# Display help message
show_help() {
    echo "Car Auction Analyzer - Deployment Script"
    echo ""
    echo "Usage: ./deploy.sh [options]"
    echo "  Options:"
    echo "    -e, --environment ENV    Deployment environment (staging|production)"
    echo "    -t, --tag TAG            Docker image tag (default: date-based)"
    echo "    -s, --skip-build         Skip building images"
    echo "    -f, --force              Force deployment without confirmation"
    echo "    -h, --help               Show this help message"
    echo ""
    echo "Example: ./deploy.sh --environment production --tag v1.2.3"
    exit 0
}

# Log messages to console and log file
log() {
    local level=$1
    local message=$2
    local color=$NC
    
    case $level in
        "INFO") color=$BLUE ;;
        "SUCCESS") color=$GREEN ;;
        "WARNING") color=$YELLOW ;;
        "ERROR") color=$RED ;;
    esac
    
    echo -e "${color}[$(date +'%Y-%m-%d %H:%M:%S')] [$level] $message${NC}" | tee -a "$LOG_FILE"
}

# Check if a command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Validate required tools are installed
validate_tools() {
    log "INFO" "Validating required tools..."
    
    local required_tools=("docker" "docker-compose" "curl" "jq")
    local missing_tools=()
    
    for tool in "${required_tools[@]}"; do
        if ! command_exists "$tool"; then
            missing_tools+=("$tool")
        fi
    done
    
    if [ ${#missing_tools[@]} -ne 0 ]; then
        log "ERROR" "Missing required tools: ${missing_tools[*]}"
        log "ERROR" "Please install the missing tools and try again."
        exit 1
    fi
    
    log "SUCCESS" "All required tools are installed."
}

# Validate environment file exists and has required variables
validate_environment() {
    log "INFO" "Validating environment configuration..."
    
    # Check if environment file exists
    if [ ! -f "$PROJECT_ROOT/$ENV_FILE" ]; then
        log "ERROR" "Environment file not found: $ENV_FILE"
        log "ERROR" "Please create the environment file and try again."
        exit 1
    fi
    
    # Load environment variables
    set -a
    source "$PROJECT_ROOT/$ENV_FILE"
    set +a
    
    # Check required variables
    local required_vars=(
        "DATABASE_URL" "REDIS_URL" "MINIO_ENDPOINT" "MINIO_ACCESS_KEY" 
        "MINIO_SECRET_KEY" "MINIO_BUCKET_IMAGES" "SECRET_KEY" "ALLOWED_ORIGINS"
        "API_DOMAIN" "ACME_EMAIL"
    )
    
    local missing_vars=()
    
    for var in "${required_vars[@]}"; do
        if [ -z "${!var}" ]; then
            missing_vars+=("$var")
        fi
    done
    
    if [ ${#missing_vars[@]} -ne 0 ]; then
        log "ERROR" "Missing required environment variables: ${missing_vars[*]}"
        log "ERROR" "Please update your $ENV_FILE file and try again."
        exit 1
    fi
    
    # Set the Docker registry and tag in environment
    export DOCKER_REGISTRY=${DOCKER_REGISTRY:-"ghcr.io"}
    export TAG=${TAG:-$DEFAULT_TAG}
    
    log "SUCCESS" "Environment configuration validated."
}

# Build and tag Docker images
build_images() {
    if [ "$SKIP_BUILD" = true ]; then
        log "INFO" "Skipping image build as requested."
        return 0
    fi
    
    log "INFO" "Building Docker images with tag: $TAG"
    
    # Navigate to project root
    cd "$PROJECT_ROOT"
    
    # Build images using docker-compose
    if ! docker-compose -f "$DOCKER_COMPOSE_FILE" build --pull; then
        log "ERROR" "Failed to build Docker images."
        exit 1
    fi
    
    # Tag images for the registry
    local services=("api" "worker" "beat" "flower")
    local image_name="${DOCKER_REGISTRY}/$(whoami)/car-auction-analyzer"
    
    for service in "${services[@]}"; do
        if ! docker tag "car-auction-analyzer_${service}" "${image_name}:${TAG}"; then
            log "ERROR" "Failed to tag image for service: $service"
            exit 1
        fi
    done
    
    log "SUCCESS" "Docker images built and tagged successfully."
}

# Push Docker images to registry
push_images() {
    if [ "$SKIP_BUILD" = true ]; then
        log "INFO" "Skipping image push as build was skipped."
        return 0
    fi
    
    log "INFO" "Pushing Docker images to registry: $DOCKER_REGISTRY"
    
    # Check if user is logged in to Docker registry
    if ! docker info | grep -q "Username"; then
        log "WARNING" "Not logged in to Docker registry."
        log "WARNING" "Please login with: docker login $DOCKER_REGISTRY"
        
        # Prompt for login if not forced
        if [ "$FORCE" != true ]; then
            read -p "Do you want to login now? (y/n): " login_choice
            if [[ "$login_choice" =~ ^[Yy]$ ]]; then
                docker login "$DOCKER_REGISTRY"
            else
                log "ERROR" "Docker registry login required to push images."
                exit 1
            fi
        else
            log "ERROR" "Docker registry login required to push images."
            exit 1
        fi
    fi
    
    # Push images
    local image_name="${DOCKER_REGISTRY}/$(whoami)/car-auction-analyzer:${TAG}"
    if ! docker push "$image_name"; then
        log "ERROR" "Failed to push Docker images to registry."
        exit 1
    fi
    
    log "SUCCESS" "Docker images pushed to registry successfully."
}

# Run database migrations
run_migrations() {
    log "INFO" "Running database migrations..."
    
    # Check if database is accessible
    if ! docker-compose -f "$DOCKER_COMPOSE_FILE" run --rm api python -c "from app.db.session import engine; print('Database connection successful')"; then
        log "ERROR" "Failed to connect to database. Please check your DATABASE_URL."
        exit 1
    fi
    
    # Create database backup before migration
    log "INFO" "Creating database backup before migration..."
    local backup_file="db_backup_before_deploy_${TAG}.sql"
    if ! docker-compose -f "$DOCKER_COMPOSE_FILE" exec -T db pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" -f "/backups/$backup_file"; then
        log "WARNING" "Failed to create database backup. Proceeding without backup."
    else
        log "SUCCESS" "Database backup created: $backup_file"
    fi
    
    # Run migrations
    if ! docker-compose -f "$DOCKER_COMPOSE_FILE" run --rm api alembic upgrade head; then
        log "ERROR" "Database migration failed."
        log "INFO" "Attempting to restore database from backup..."
        
        if docker-compose -f "$DOCKER_COMPOSE_FILE" exec -T db psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -f "/backups/$backup_file"; then
            log "SUCCESS" "Database restored from backup."
        else
            log "ERROR" "Failed to restore database from backup."
        fi
        
        exit 1
    fi
    
    log "SUCCESS" "Database migrations completed successfully."
}

# Deploy services
deploy_services() {
    log "INFO" "Deploying services to $ENVIRONMENT environment..."
    
    # Pull latest images if not building locally
    if [ "$SKIP_BUILD" = true ]; then
        log "INFO" "Pulling latest images from registry..."
        if ! docker-compose -f "$DOCKER_COMPOSE_FILE" pull; then
            log "ERROR" "Failed to pull latest images from registry."
            exit 1
        fi
    fi
    
    # Stop and remove existing containers
    log "INFO" "Stopping existing services..."
    docker-compose -f "$DOCKER_COMPOSE_FILE" down --remove-orphans || true
    
    # Start services
    log "INFO" "Starting services..."
    if ! docker-compose -f "$DOCKER_COMPOSE_FILE" up -d; then
        log "ERROR" "Failed to start services."
        exit 1
    fi
    
    log "SUCCESS" "Services deployed successfully."
}

# Check health of deployed services
check_health() {
    log "INFO" "Checking health of deployed services..."
    
    # Wait for services to be ready
    log "INFO" "Waiting for services to be ready (timeout: ${DEPLOYMENT_TIMEOUT}s)..."
    local start_time=$(date +%s)
    local current_time=0
    local elapsed_time=0
    local healthy=false
    
    while [ $elapsed_time -lt $DEPLOYMENT_TIMEOUT ]; do
        # Check API health endpoint
        if curl -s -o /dev/null -w "%{http_code}" "https://${API_DOMAIN}/api/health" | grep -q "200"; then
            healthy=true
            break
        fi
        
        log "INFO" "Services not ready yet, waiting 10 seconds..."
        sleep 10
        
        current_time=$(date +%s)
        elapsed_time=$((current_time - start_time))
    done
    
    if [ "$healthy" = true ]; then
        log "SUCCESS" "Services are healthy and ready."
    else
        log "ERROR" "Services failed to become healthy within timeout period."
        log "ERROR" "Deployment failed, initiating rollback..."
        rollback
        exit 1
    fi
}

# Rollback deployment
rollback() {
    log "WARNING" "Rolling back deployment..."
    
    # Get previous deployment tag
    local previous_tag=$(docker-compose -f "$DOCKER_COMPOSE_FILE" config | grep "image:" | grep "${DOCKER_REGISTRY}" | head -1 | sed -E "s/.*:([^\"]+)\"/\1/")
    
    if [ -z "$previous_tag" ] || [ "$previous_tag" = "$TAG" ]; then
        log "WARNING" "No previous deployment found or same as current. Rolling back to last known good state."
        previous_tag="latest"
    fi
    
    log "INFO" "Rolling back to tag: $previous_tag"
    
    # Set previous tag
    export TAG=$previous_tag
    
    # Stop current services
    docker-compose -f "$DOCKER_COMPOSE_FILE" down --remove-orphans || true
    
    # Start services with previous tag
    if ! docker-compose -f "$DOCKER_COMPOSE_FILE" up -d; then
        log "ERROR" "Failed to rollback to previous version."
        log "ERROR" "Manual intervention required!"
        exit 1
    fi
    
    log "SUCCESS" "Rollback completed successfully."
}

# Update frontend deployment
deploy_frontend() {
    log "INFO" "Deploying frontend to Netlify..."
    
    # Check if Netlify CLI is installed
    if ! command_exists netlify; then
        log "WARNING" "Netlify CLI not found. Skipping automated frontend deployment."
        log "INFO" "To deploy frontend manually:"
        log "INFO" "1. Navigate to Netlify dashboard"
        log "INFO" "2. Drag and drop the 'docs/' folder or connect to your GitHub repository"
        return 0
    fi
    
    # Check if user is logged in to Netlify
    if ! netlify status | grep -q "Logged in"; then
        log "WARNING" "Not logged in to Netlify."
        log "INFO" "Please login with: netlify login"
        return 0
    fi
    
    # Deploy to Netlify
    cd "$PROJECT_ROOT"
    if ! netlify deploy --dir=docs --prod; then
        log "ERROR" "Failed to deploy frontend to Netlify."
        return 1
    fi
    
    log "SUCCESS" "Frontend deployed to Netlify successfully."
    return 0
}

# Main deployment process
deploy() {
    log "INFO" "Starting deployment process for environment: $ENVIRONMENT"
    
    # Create deployment directory
    mkdir -p "$PROJECT_ROOT/deployments"
    cd "$PROJECT_ROOT"
    
    # Validate tools and environment
    validate_tools
    validate_environment
    
    # Confirm deployment
    if [ "$FORCE" != true ]; then
        log "WARNING" "You are about to deploy to $ENVIRONMENT environment with tag $TAG."
        read -p "Do you want to continue? (y/n): " deploy_choice
        if [[ ! "$deploy_choice" =~ ^[Yy]$ ]]; then
            log "INFO" "Deployment cancelled by user."
            exit 0
        fi
    fi
    
    # Start deployment
    build_images
    push_images
    run_migrations
    deploy_services
    check_health
    deploy_frontend
    
    # Deployment summary
    log "SUCCESS" "==================================================="
    log "SUCCESS" "Deployment completed successfully!"
    log "SUCCESS" "Environment: $ENVIRONMENT"
    log "SUCCESS" "Tag: $TAG"
    log "SUCCESS" "API URL: https://${API_DOMAIN}"
    log "SUCCESS" "==================================================="
}

# ===== PARSE COMMAND LINE ARGUMENTS =====
ENVIRONMENT="production"
TAG=$DEFAULT_TAG
SKIP_BUILD=false
FORCE=false

while [[ $# -gt 0 ]]; do
    key="$1"
    case $key in
        -e|--environment)
            ENVIRONMENT="$2"
            shift 2
            ;;
        -t|--tag)
            TAG="$2"
            shift 2
            ;;
        -s|--skip-build)
            SKIP_BUILD=true
            shift
            ;;
        -f|--force)
            FORCE=true
            shift
            ;;
        -h|--help)
            show_help
            ;;
        *)
            log "ERROR" "Unknown option: $key"
            show_help
            ;;
    esac
done

# Validate environment
if [[ ! "$ENVIRONMENT" =~ ^(staging|production)$ ]]; then
    log "ERROR" "Invalid environment: $ENVIRONMENT"
    log "ERROR" "Valid environments are: staging, production"
    exit 1
fi

# Set environment-specific files
if [ "$ENVIRONMENT" = "staging" ]; then
    DOCKER_COMPOSE_FILE="docker-compose.staging.yml"
    ENV_FILE=".env.staging"
fi

# Start deployment
deploy

exit 0
