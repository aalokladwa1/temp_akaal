# AKAAL Enterprise Multi-Region Terraform Infrastructure Manifest

terraform {
  required_version = ">= 1.5.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

provider "aws" {
  region = var.primary_region
}

variable "primary_region" {
  type    = string
  default = "us-east-1"
}

variable "secondary_region" {
  type    = string
  default = "us-west-2"
}

resource "aws_ecs_cluster" "akaal_cluster" {
  name = "akaal-enterprise-cluster"

  setting {
    name  = "containerInsights"
    value = "enabled"
  }
}
