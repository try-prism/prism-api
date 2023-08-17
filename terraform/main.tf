provider "aws" {
  region                   = var.region
  shared_credentials_files = ["$HOME/.aws/credentials"]
  profile                  = "default"
}

provider "docker" {
  registry_auth {
    address  = local.ecr_address
    password = data.aws_ecr_authorization_token.prism.password
    username = data.aws_ecr_authorization_token.prism.user_name
  }
}

data "aws_caller_identity" "prism" {}
data "aws_ecr_authorization_token" "prism" {}
data "aws_region" "prism" {}
data "aws_availability_zones" "available" {
  state = "available"
}

locals {
  container_port = 8000
  ecr_address = format(
    "%v.dkr.ecr.%v.amazonaws.com",
    data.aws_caller_identity.prism.account_id,
    data.aws_region.prism.name
  )
}

# VPC
module "vpc" {
  source = "terraform-aws-modules/vpc/aws"

  name = var.vpc_name
  cidr = "10.0.0.0/16"

  azs             = slice(data.aws_availability_zones.available.names, 0, 2)
  private_subnets = ["10.0.1.0/24", "10.0.2.0/24"]
  public_subnets  = ["10.0.101.0/24", "10.0.102.0/24"]

  enable_nat_gateway = true
  enable_vpn_gateway = true
  create_igw         = true
}

# ECR repository
module "ecr" {
  source                  = "terraform-aws-modules/ecr/aws"
  repository_name         = var.ecr_name
  repository_force_delete = true
  repository_lifecycle_policy = jsonencode({
    rules = [
      {
        rulePriority = 1,
        description  = "Keep last 5 images",
        selection = {
          tagStatus     = "tagged",
          tagPrefixList = ["v"],
          countType     = "imageCountMoreThan",
          countNumber   = 5
        },
        action = {
          type = "expire"
        }
      }
    ]
  })
}

# ECS
module "ecs" {
  source = "terraform-aws-modules/ecs/aws"

  cluster_name = var.ecs_cluster_name

  fargate_capacity_providers = {
    FARGATE = {
      default_capacity_provider_strategy = {
        base   = 20
        weight = 50
      }
    }
    FARGATE_SPOT = {
      default_capacity_provider_strategy = {
        weight = 50
      }
    }
  }
}

resource "aws_ecs_task_definition" "prism" {
  container_definitions = jsonencode([{
    "name" : "prism",
    "essential" : true,
    "image" : "${resource.docker_registry_image.prism.name}",
    "portMappings" : [
      {
        "containerPort" : 80,
      }
    ]
  }])
  cpu                      = 1024
  memory                   = 2048
  family                   = var.ecs_task_name
  execution_role_arn       = data.aws_iam_role.ecs_task_execution_role.arn
  network_mode             = "awsvpc"
  requires_compatibilities = ["FARGATE"]
}

resource "aws_ecs_service" "prism" {
  cluster         = module.ecs.cluster_id
  desired_count   = 1
  launch_type     = "FARGATE"
  name            = var.ecs_service_name
  task_definition = resource.aws_ecs_task_definition.prism.arn

  lifecycle {
    ignore_changes = [desired_count] # Allow external changes to happen without Terraform conflicts, particularly around auto-scaling.
  }

  load_balancer {
    container_name   = "prism-api"
    container_port   = local.container_port
    target_group_arn = module.alb.target_group_arns[0]
  }

  network_configuration {
    security_groups = [module.vpc.default_security_group_id]
    subnets         = module.vpc.private_subnets
  }
}

# LB 
module "alb" {
  source  = "terraform-aws-modules/alb/aws"
  version = "~> 8.0"

  name               = var.lb_name
  load_balancer_type = "application"

  vpc_id          = module.vpc.vpc_id
  subnets         = module.vpc.public_subnets
  security_groups = [module.vpc.default_security_group_id]

  security_group_rules = {
    ingress_all_http = {
      type        = "ingress"
      from_port   = 80
      to_port     = 80
      protocol    = "TCP"
      description = "Permit incoming HTTP requests from the internet"
      cidr_blocks = ["0.0.0.0/0"]
    }
    egress_all = {
      type        = "egress"
      from_port   = 0
      to_port     = 0
      protocol    = "-1"
      description = "Permit all outgoing requests to the internet"
      cidr_blocks = ["0.0.0.0/0"]
    }
  }

  http_tcp_listeners = [
    {
      port               = 80
      protocol           = "HTTP"
      target_group_index = 0
    }
  ]

  target_groups = [
    {
      backend_port     = local.container_port
      backend_protocol = "HTTP"
      target_type      = "ip"
    }
  ]
}

# Docker
resource "docker_image" "prism" {
  name = format(
    "%v:%v",
    module.ecr.repository_url,
    formatdate(
      "YYYY-MM-DD'T'hh-mm-ss",
      timestamp()
    )
  )

  build {
    context = "../" # Path to local Dockerfile
  }
}

resource "docker_registry_image" "prism" {
  keep_remotely = true
  name          = resource.docker_image.prism.name
}

# Output URL
output "url" {
  value = "http://${module.alb.lb_dns_name}"
}
