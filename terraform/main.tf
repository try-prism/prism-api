provider "aws" {
  region = local.region
}

locals {
  region = "us-east-1"
}

# ECR repository
resource "aws_ecr_repository" "prismapi" {
  name = var.ecr_name
}

# ECS cluster
resource "aws_ecs_cluster" "prismapi" {
  name = var.ecs_cluster_name
}

# ECS task definition
resource "aws_ecs_task_definition" "prismapi" {
  family                   = var.ecs_task_name
  requires_compatibilities = ["FARGATE"]
  network_mode             = "awsvpc"
  cpu                      = 1024
  memory                   = 2048
  container_definitions = jsonencode([
    {
      "name" : "prismapi",
      "image" : "${aws_ecr_repository.prismapi.repository_url}:latest",
      "portMappings" : [
        {
          "containerPort" : 80,
          "hostPort" : 80
        }
      ]
    }
  ])
}

# VPC
resource "aws_vpc" "main" {
  cidr_block = "10.0.0.0/16"
}

# Public subnets
resource "aws_subnet" "public_1" {
  vpc_id     = aws_vpc.main.id
  cidr_block = "10.0.1.0/24"
}
resource "aws_subnet" "public_2" {
  vpc_id     = aws_vpc.main.id
  cidr_block = "10.0.2.0/24"
}

# ECS service
resource "aws_ecs_service" "prismapi" {
  name            = var.ecs_service_name
  cluster         = aws_ecs_cluster.prismapi.id
  task_definition = aws_ecs_task_definition.prismapi.arn
  desired_count   = 1
}

# LB 
resource "aws_lb" "prismapi" {
  name     = var.lb_name
  internal = false

  load_balancer_type = "application"
  subnets = [
    aws_subnet.public_1.id,
    aws_subnet.public_2.id
  ]
}

# LB Target Group
resource "aws_lb_target_group" "prismapi" {
  name     = var.target_group_name
  port     = 80
  protocol = "HTTP"
  vpc_id   = aws_vpc.main.id
}

# LB listener
resource "aws_lb_listener" "prismapi" {
  load_balancer_arn = aws_lb.prismapi.arn
  port              = 80
  protocol          = "HTTP"

  default_action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.prismapi.arn
  }
}
