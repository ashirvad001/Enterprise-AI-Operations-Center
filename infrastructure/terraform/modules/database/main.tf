variable "environment" { type = string }
variable "vpc_id" { type = string }
variable "subnet_ids" { type = list(string) }

resource "aws_db_subnet_group" "db_subnet_group" {
  name       = "eaioc-db-subnet-group-${var.environment}"
  subnet_ids = var.subnet_ids
}

resource "aws_security_group" "rds_sg" {
  name        = "eaioc-rds-sg-${var.environment}"
  vpc_id      = var.vpc_id

  ingress {
    from_port   = 5432
    to_port     = 5432
    protocol    = "tcp"
    cidr_blocks = ["10.0.0.0/16"] # Restricted to VPC CIDR
  }
}

resource "aws_db_instance" "postgres" {
  identifier           = "eaioc-db-${var.environment}"
  allocated_storage    = 50
  engine               = "postgres"
  engine_version       = "15.4" # Ensures pgvector compatibility
  instance_class       = "db.t4g.large"
  db_name              = "eaioc_db"
  username             = "eaioc_admin"
  password             = "super_secret_managed_by_secrets_manager" # Placeholder
  
  db_subnet_group_name = aws_db_subnet_group.db_subnet_group.name
  vpc_security_group_ids = [aws_security_group.rds_sg.id]
  
  skip_final_snapshot  = true
}

output "db_endpoint" {
  value = aws_db_instance.postgres.endpoint
}
