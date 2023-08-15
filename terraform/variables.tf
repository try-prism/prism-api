# ECR
variable "ecr_name" {
  description = "Name of the ECR repository"
  type        = string
  default     = "prism-ecr"
}

# ECS 
variable "ecs_cluster_name" {
  description = "Name of the ECS cluster"
  type        = string
  default     = "prism-cluster"
}

variable "ecs_task_name" {
  description = "Name of the ECS task definition"
  type        = string
  default     = "prism-task"
}

variable "ecs_task_role_name" {
  description = "Name of the ECS task role"
  type        = string
  default     = "prism-ecs-task-role"
}

variable "ecs_task_execution_role_name" {
  description = "Name of the ECS task execution role"
  type        = string
  default     = "prism-ecs-task-execution-role"
}

variable "ecs_service_name" {
  description = "Name of the ECS service"
  type        = string
  default     = "prism-service"
}

# VPC
variable "vpc_name" {
  description = "Name of the VPC"
  type        = string
  default     = "prism-vpc"
}

# LB
variable "lb_name" {
  description = "Name of the Application Load Balancer"
  type        = string
  default     = "prism-lb"
}

variable "target_group_name" {
  description = "Name of the LB target group"
  type        = string
  default     = "prism-tg"
}
