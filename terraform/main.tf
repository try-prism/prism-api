provider "aws" {
  region                   = local.region
  shared_credentials_files = ["$HOME/.aws/credentials"]
  profile                  = "default"
}

locals {
  region = "us-east-1"
}

# VPC
module "vpc" {
  source = "terraform-aws-modules/vpc/aws"

  name = var.vpc_name
  cidr = "10.0.0.0/16"

  azs             = ["us-east-1a", "us-east-1b"]
  private_subnets = ["10.0.1.0/24", "10.0.2.0/24"]
  public_subnets  = ["10.0.101.0/24", "10.0.102.0/24"]

  enable_nat_gateway = true
  enable_vpn_gateway = true
}

# ECR repository
resource "aws_ecr_repository" "prism" {
  name = var.ecr_name
}

# ECS cluster
resource "aws_ecs_cluster" "prism" {
  name = var.ecs_cluster_name
}

# ECS task definition
resource "aws_ecs_task_definition" "prism" {
  family                   = var.ecs_task_name
  requires_compatibilities = ["FARGATE"]
  network_mode             = "awsvpc"
  cpu                      = 1024
  memory                   = 2048
  execution_role_arn       = data.aws_iam_role.ecs_task_execution_role.arn
  container_definitions = jsonencode([
    {
      "name" : "prism",
      "image" : "${aws_ecr_repository.prism.repository_url}:latest",
      "portMappings" : [
        {
          "containerPort" : 80,
          "hostPort" : 80
        }
      ]
    }
  ])
}

# ECS service
resource "aws_ecs_service" "prism" {
  name            = var.ecs_service_name
  cluster         = aws_ecs_cluster.prism.id
  task_definition = aws_ecs_task_definition.prism.arn
  desired_count   = 1
  network_configuration {
    subnets = module.vpc.private_subnets
  }
}

# LB 
resource "aws_lb" "prism" {
  name     = var.lb_name
  internal = false

  load_balancer_type = "application"
  subnets            = module.vpc.public_subnets
}

# LB Target Group
resource "aws_lb_target_group" "prism" {
  name     = var.target_group_name
  port     = 80
  protocol = "HTTP"
  vpc_id   = module.vpc.vpc_id
}

# LB listener
resource "aws_lb_listener" "prism" {
  load_balancer_arn = aws_lb.prism.arn
  port              = 80
  protocol          = "HTTP"

  default_action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.prism.arn
  }
}
