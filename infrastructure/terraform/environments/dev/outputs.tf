output "vpc_id" {
  value = module.vpc.vpc_id
}

output "database_endpoint" {
  value = module.database.db_endpoint
}

output "redis_endpoint" {
  value = module.cache.redis_endpoint
}

output "assets_bucket" {
  value = module.storage.assets_bucket_name
}

output "kubernetes_cluster_endpoint" {
  value = module.eks.cluster_endpoint
}
