terraform {
  backend "s3" {
    bucket = "prism-api-terraform"
    key    = "shared/terraform.tfstate"
    region = "us-east-1"
  }
}
