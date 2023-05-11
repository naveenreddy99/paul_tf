resource "aws_iam_policy" "lambda_execution_policy" {
  name        = "LambdaEC2S3_Devolumizer_Policy"
  description = "Policy for Lambda function with EC2 and S3 full access"

  policy = <<EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "ec2:*",
        "s3:*"
      ],
      "Resource": "*"
    }
  ]
}
EOF
}

resource "aws_iam_role_policy_attachment" "lambda_execution_policy_attachment" {
  role       = aws_iam_role.LambdaExecutionRole.name
  policy_arn = aws_iam_policy.lambda_execution_policy.arn
}

/* Lambda Execution Role Creation */
resource "aws_iam_role" "LambdaExecutionRole" {
  name = var.lambda_execution_role_name

  # Terraform's "jsonencode" function converts a
  # Terraform expression result to valid JSON syntax.
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Sid    = ""
        Principal = {
          Service = "lambda.amazonaws.com"
        }
      },
    ]
  })
}

/* Devolumizer LAMBDA FUNCTION */
data "archive_file" "devolumizer_lambda_zip_file" {
  type            = "zip"
  source_file     = "./dv6.py"
  output_path     = "./devolumizer.py.zip"
}

resource "aws_lambda_function" "devolumizer_lambda" {
  filename          = "devolumizer.py.zip"
  source_code_hash  = filebase64sha256(data.archive_file.devolumizer_lambda_zip_file.output_path)
  function_name     = var.devolumizer_function_name
  role              = aws_iam_role.LambdaExecutionRole.arn
  handler           = "lambda_function.lambda_handler"

  # The filebase64sha256() function is available in Terraform 0.11.12 and later
  # For Terraform 0.11.11 and earlier, use the base64sha256() function and the file() function:
  # source_code_hash = "${base64sha256(file("lambda_function_payload.zip"))}"
  #source_code_hash = filebase64sha256("lambda_function_payload.zip")

  runtime = "python3.10"
  memory_size = 128
  timeout = 300
}

resource "aws_cloudwatch_event_rule" "lambda_schedule" {
  name        = "devolumizer-lambda-schedule-rule"
  description = "Schedule for Lambda function"

  schedule_expression = "cron(0 0 * * ? *)"  # Runs every day at 12:00 AM UTC

  tags = {
    Name = "devolumizer-lambda-schedule-rule"
  }
}

resource "aws_cloudwatch_event_target" "lambda_target" {
  rule      = aws_cloudwatch_event_rule.lambda_schedule.name
  target_id = "lambda-target"

  arn = aws_lambda_function.devolumizer_lambda.arn
}