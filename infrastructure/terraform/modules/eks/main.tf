variable "environment" { type = string }
variable "vpc_id" { type = string }
variable "subnet_ids" { type = list(string) }

module "eks" {
  source  = "terraform-aws-modules/eks/aws"
  version = "19.21.0"

  cluster_name    = "eaioc-cluster-${var.environment}"
  cluster_version = "1.28"

  vpc_id                   = var.vpc_id
  subnet_ids               = var.subnet_ids
  control_plane_subnet_ids = var.subnet_ids

  eks_managed_node_groups = {
    general_workload = {
      min_size     = 2
      max_size     = 5
      desired_size = 2
      
      instance_types = ["t3.xlarge"]
    }
  }

  tags = {
    Environment = var.environment
  }
}

output "cluster_endpoint" {
  value = module.eks.cluster_endpoint
}

output "cluster_name" {
  value = module.eks.cluster_name
}
