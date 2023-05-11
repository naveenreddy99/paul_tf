import boto3
import csv
from datetime import datetime, timedelta

# create an S3 client
s3 = boto3.client('s3')

# set the TTL for empty buckets (in days)
TTL_DAYS = 0

# Generate a unique report filename based on the current date and time
now = datetime.now()
report_date = now.strftime('%Y-%m-%d-%H-%M-%S')
report_filename = f's3-bucket-report-{report_date}.csv'

# The name of the S3 bucket to store the report
report_bucket_name = 'kshdflk8ksajdlkfsa'
    
# set the date format
DATE_FORMAT = '%Y-%m-%d %H:%M:%S'

def lambda_handler(event, context):
    # get the list of buckets
    buckets = s3.list_buckets()

    # initialize the report data
    report_data = [['Bucket Name', 'Creation Date', 'Expiration Date', 'Status']]

    # initialize the counters
    total_buckets = len(buckets['Buckets'])
    deleted_buckets = 0

    # iterate through each bucket
    for bucket in buckets['Buckets']:
        # get the bucket name and creation date
        bucket_name = bucket['Name']
        bucket_creation_date = bucket['CreationDate'].strftime('%Y-%m-%dT%H:%M:%S.%fZ')
        
        # check if the bucket is empty
        bucket_objects = s3.list_objects_v2(Bucket=bucket_name)
        if bucket_objects['KeyCount'] == 0:
            # calculate the expiration date
            expiration_date = datetime.strptime(bucket_creation_date, '%Y-%m-%dT%H:%M:%S.%fZ') + timedelta(days=TTL_DAYS)
            
            # add the expiration tag to the bucket
            s3.put_bucket_tagging(Bucket=bucket_name, Tagging={'TagSet': [{'Key': 'ExpirationDate', 'Value': expiration_date.strftime('%Y-%m-%d')}]})
            
            # check if the expiration date has passed
            if datetime.utcnow() > expiration_date:
                # delete the bucket
                s3.delete_bucket(Bucket=bucket_name)
                deleted_buckets += 1
                report_data.append([bucket_name, bucket_creation_date, expiration_date.strftime(DATE_FORMAT), 'Deleted'])
            else:
                report_data.append([bucket_name, bucket_creation_date, expiration_date.strftime(DATE_FORMAT), 'TTL Added'])
        else:
            report_data.append([bucket_name, bucket_creation_date, '', 'Skipped, Non-Empty Bucket'])

    # create the report file in CSV format
    report_file = '/tmp/report.csv'
    with open(report_file, mode='w', newline='') as csv_file:
        writer = csv.writer(csv_file)
        for row in report_data:
            writer.writerow(row)

    # upload the report to S3
    s3.upload_file(report_file, report_bucket_name, 's3_report/' + report_filename)
    
    # print the report
    print(f'Total buckets: {total_buckets}')
    print(f'Deleted buckets: {deleted_buckets}')
    print(f'Empty buckets with TTL: {total_buckets-deleted_buckets}')
    
    # Print the S3 URL of the report
    report_url = f's3://{report_bucket_name}/s3_report/{report_filename}'
    print(f'Report URL: {report_url}')
