# Development environment main configuration
terraform {
  required_version = ">= 1.0"
  
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
    kubernetes = {
      source  = "hashicorp/kubernetes"
      version = "~> 2.20"
    }
    helm = {
      source  = "hashicorp/helm"
      version = "~> 2.10"
    }
  }

  backend "s3" {
    bucket = "cloud-app-terraform-state-dev"
    key    = "dev/terraform.tfstate"
    region = "us-east-1"
    
    dynamodb_table = "terraform-state-lock"
    encrypt        = true
  }
}

provider "aws" {
  region = var.aws_region

  default_tags {
    tags = {
      Environment   = "development"
      Project       = "cloud-app"
      ManagedBy     = "terraform"
      Owner         = "platform-team"
    }
  }
}

# Data sources
data "aws_availability_zones" "available" {
  state = "available"
}

# Local values
locals {
  name_prefix = "cloud-app-dev"
  
  common_tags = {
    Environment = "development"
    Project     = "cloud-app"
    ManagedBy   = "terraform"
  }
}

# Networking
module "networking" {
  source = "../../modules/networking"
  
  name_prefix         = local.name_prefix
  vpc_cidr           = var.vpc_cidr
  availability_zones = data.aws_availability_zones.available.names
  
  tags = local.common_tags
}

# EKS Cluster
module "eks" {
  source = "../../modules/eks"
  
  cluster_name       = "${local.name_prefix}-cluster"
  kubernetes_version = var.kubernetes_version
  
  vpc_id                = module.networking.vpc_id
  subnet_ids           = module.networking.public_subnet_ids
  private_subnet_ids   = module.networking.private_subnet_ids
  public_access_cidrs  = var.allowed_cidr_blocks
  
  node_instance_types = var.node_instance_types
  node_desired_size   = var.node_desired_size
  node_max_size       = var.node_max_size
  node_min_size       = var.node_min_size
  
  tags = local.common_tags
}

# RDS for UserProfiles
module "rds" {
  source = "../../modules/rds"
  
  name_prefix    = local.name_prefix
  vpc_id         = module.networking.vpc_id
  subnet_ids     = module.networking.private_subnet_ids
  
  engine_version     = var.postgres_version
  instance_class     = var.rds_instance_class
  allocated_storage  = var.rds_allocated_storage
  
  database_name = "userprofiles"
  master_username = "dbadmin"
  
  backup_retention_period = 7
  backup_window          = "03:00-04:00"
  maintenance_window     = "sun:04:00-sun:05:00"
  
  tags = local.common_tags
}

# ElastiCache Redis for Sessions
module "redis" {
  source = "../../modules/redis"
  
  name_prefix = local.name_prefix
  vpc_id      = module.networking.vpc_id
  subnet_ids  = module.networking.private_subnet_ids
  
  node_type         = var.redis_node_type
  num_cache_nodes   = var.redis_num_nodes
  engine_version    = var.redis_version
  
  tags = local.common_tags
}

# DynamoDB for UserSettings
module "dynamodb" {
  source = "../../modules/dynamodb"
  
  name_prefix = local.name_prefix
  
  tables = {
    user_settings = {
      hash_key  = "user_id"
      range_key = "category"
      attributes = [
        {
          name = "user_id"
          type = "S"
        },
        {
          name = "category"
          type = "S"
        }
      ]
      ttl_enabled = true
      ttl_attribute = "ttl_epoch_s"
    }
    
    usersettings_migrations = {
      hash_key = "id"
      attributes = [
        {
          name = "id"
          type = "S"
        }
      ]
    }
  }
  
  tags = local.common_tags
}

# MSK for Events
module "msk" {
  source = "../../modules/msk"
  
  name_prefix = local.name_prefix
  vpc_id      = module.networking.vpc_id
  subnet_ids  = module.networking.private_subnet_ids
  
  kafka_version   = var.kafka_version
  instance_type   = var.msk_instance_type
  number_of_nodes = var.msk_number_of_nodes
  
  tags = local.common_tags
}

# Cognito for Authentication
module "cognito" {
  source = "../../modules/cognito"
  
  name_prefix = local.name_prefix
  
  domain_name = "${local.name_prefix}-auth"
  
  tags = local.common_tags
}

# API Gateway
module "api_gateway" {
  source = "../../modules/api_gateway"
  
  name_prefix = local.name_prefix
  
  domain_name        = "api-dev.example.com"
  certificate_arn    = var.ssl_certificate_arn
  
  # Target NLB (will be created by EKS)
  target_nlb_dns = module.eks.cluster_endpoint
  
  tags = local.common_tags
}

# Observability
module "observability" {
  source = "../../modules/observability"
  
  name_prefix    = local.name_prefix
  eks_cluster_id = module.eks.cluster_id
  
  tags = local.common_tags
}