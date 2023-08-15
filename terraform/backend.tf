terraform {
  backend "s3" {
    bucket = "prism-terraform"
    key    = "shared/terraform.tfstate"
    region = "us-east-1"
  }
}
