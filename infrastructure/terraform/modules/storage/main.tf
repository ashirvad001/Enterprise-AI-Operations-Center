variable "environment" { type = string }

resource "aws_s3_bucket" "assets" {
  bucket = "eaioc-assets-${var.environment}"
}

resource "aws_s3_bucket_public_access_block" "assets_block" {
  bucket = aws_s3_bucket.assets.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket" "models" {
  bucket = "eaioc-models-${var.environment}"
}

output "assets_bucket_name" {
  value = aws_s3_bucket.assets.id
}
