terraform {
  backend "s3" {
    bucket = "prism-terraform-s3"
    key    = "shared/terraform.tfstate"
    region = "us-east-1"
  }
}
