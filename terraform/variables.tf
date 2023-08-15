# ECR
variable "ecr_name" {
  description = "Name of the ECR repository"
  type        = string
  default     = "prism-api-ecr"
}

# ECS 
variable "ecs_cluster_name" {
  description = "Name of the ECS cluster"
  type        = string
  default     = "prism-api-cluster"
}

variable "ecs_task_name" {
  description = "Name of the ECS task definition"
  type        = string
  default     = "prism-api-task"
}

variable "ecs_service_name" {
  description = "Name of the ECS service"
  type        = string
  default     = "prism-api-service"
}

# VPC
variable "vpc_name" {
  description = "Name of the VPC"
  type        = string
  default     = "prism-api-vpc"
}

# LB
variable "lb_name" {
  description = "Name of the Application Load Balancer"
  type        = string
  default     = "prism-api-lb"
}

variable "target_group_name" {
  description = "Name of the LB target group"
  type        = string
  default     = "prism-api-tg"
}
