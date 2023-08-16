resource "aws_iam_role_policy_attachment" "ecs-task-execution-role-policy-attachment" {
  role       = var.ecs_task_execution_role_name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy"
}

data "aws_iam_role" "ecs_task_execution_role" {
  name = var.ecs_task_execution_role_name
}
